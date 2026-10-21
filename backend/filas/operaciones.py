"""Operaciones sobre tickets.

Toda modificación de un ticket pasa por aquí: valida la transición de estado,
actualiza el ticket y registra el EventoTicket en la misma transacción.
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import ContadorDiario, EventoTicket, Puesto, Servicio, Ticket

Estado = Ticket.Estado
Tipo = EventoTicket.Tipo


class OperacionInvalida(Exception):
    pass


def _registrar(ticket, tipo, momento, *, funcionario=None, puesto=None, servicio_destino=None, **datos):
    return EventoTicket.objects.create(
        ticket=ticket,
        tipo=tipo,
        momento=momento,
        servicio=ticket.servicio,
        servicio_destino=servicio_destino,
        puesto=puesto,
        funcionario=funcionario,
        datos=datos,
    )


def _bloquear(ticket, *estados_permitidos):
    ticket = Ticket.objects.select_for_update().select_related("servicio").get(pk=ticket.pk)
    if ticket.estado not in estados_permitidos:
        raise OperacionInvalida(f"El ticket {ticket.codigo} está {ticket.get_estado_display().lower()}.")
    return ticket


@transaction.atomic
def emitir_ticket(servicio, *, totem=None, preferente=False):
    servicio = Servicio.objects.select_related("unidad").get(pk=servicio.pk)
    if not servicio.activo or not servicio.unidad.activa:
        raise OperacionInvalida(f"El servicio {servicio.nombre} no está disponible.")

    ahora = timezone.now()
    hoy = timezone.localdate(ahora)
    ContadorDiario.objects.get_or_create(servicio=servicio, fecha=hoy)
    contador = ContadorDiario.objects.select_for_update().get(servicio=servicio, fecha=hoy)
    if servicio.max_tickets_dia is not None and contador.emitidos >= servicio.max_tickets_dia:
        raise OperacionInvalida(f"Se alcanzó el máximo de tickets del día para {servicio.nombre}.")

    numero = contador.ultimo_numero % servicio.numero_maximo + 1
    contador.emitidos += 1
    contador.ultimo_numero = numero
    contador.save(update_fields=["emitidos", "ultimo_numero"])

    ancho = len(str(servicio.numero_maximo))
    ticket = Ticket.objects.create(
        unidad=servicio.unidad,
        servicio=servicio,
        fecha=hoy,
        numero=numero,
        codigo=f"{servicio.letra}-{numero:0{ancho}d}",
        preferente=preferente,
        totem=totem,
        emitido_en=ahora,
        en_espera_desde=ahora,
    )
    _registrar(ticket, Tipo.EMITIDO, ahora, totem_id=totem.pk if totem else None, preferente=preferente)
    return ticket


def _orden_de_llamado(ticket, ahora):
    """Clave de orden: preferentes, luego tickets envejecidos, luego prioridad del servicio y llegada."""
    espera_min = (ahora - ticket.en_espera_desde).total_seconds() / 60
    envejecido = espera_min >= ticket.servicio.minutos_envejecimiento
    return (not ticket.preferente, not envejecido, ticket.servicio.prioridad, ticket.en_espera_desde, ticket.pk)


def candidatos(puesto, ahora=None):
    """Tickets en espera que el puesto puede llamar, en el orden en que se llamarían."""
    ahora = ahora or timezone.now()
    tickets = Ticket.objects.filter(
        unidad_id=puesto.unidad_id,
        estado=Estado.EN_ESPERA,
        fecha=timezone.localdate(ahora),
        servicio__in=puesto.servicios.filter(activo=True),
    ).select_related("servicio")
    return sorted(tickets, key=lambda t: _orden_de_llamado(t, ahora))


def ticket_activo(puesto):
    return Ticket.objects.filter(puesto=puesto, estado__in=[Estado.LLAMADO, Estado.EN_ATENCION]).first()


@transaction.atomic
def llamar_siguiente(puesto, funcionario):
    """Cierra el ticket en curso del puesto (si hay) y llama al siguiente. Devuelve None si no hay nadie."""
    puesto = Puesto.objects.select_for_update().get(pk=puesto.pk)
    if not puesto.activo:
        raise OperacionInvalida(f"El puesto {puesto.nombre} está deshabilitado.")

    actual = ticket_activo(puesto)
    if actual is not None:
        if actual.estado == Estado.EN_ATENCION:
            finalizar(actual, funcionario)
        else:
            no_se_presento(actual, funcionario)

    ahora = timezone.now()
    for candidato in candidatos(puesto, ahora):
        # skip_locked: si otro puesto está tomando este mismo ticket, se pasa al siguiente.
        ticket = (
            Ticket.objects.select_for_update(skip_locked=True)
            .select_related("servicio")
            .filter(pk=candidato.pk, estado=Estado.EN_ESPERA)
            .first()
        )
        if ticket is None:
            continue
        ticket.estado = Estado.LLAMADO
        ticket.puesto = puesto
        ticket.funcionario = funcionario
        ticket.llamado_en = ahora
        ticket.veces_llamado = 1
        ticket.save(update_fields=["estado", "puesto", "funcionario", "llamado_en", "veces_llamado"])
        _registrar(ticket, Tipo.LLAMADO, ahora, funcionario=funcionario, puesto=puesto)
        return ticket
    return None


@transaction.atomic
def rellamar(ticket, funcionario):
    ticket = _bloquear(ticket, Estado.LLAMADO)
    ahora = timezone.now()
    ticket.veces_llamado = F("veces_llamado") + 1
    ticket.save(update_fields=["veces_llamado"])
    ticket.refresh_from_db()
    _registrar(ticket, Tipo.RELLAMADO, ahora, funcionario=funcionario, puesto=ticket.puesto, vez=ticket.veces_llamado)
    return ticket


@transaction.atomic
def iniciar_atencion(ticket, funcionario):
    ticket = _bloquear(ticket, Estado.LLAMADO)
    ahora = timezone.now()
    ticket.estado = Estado.EN_ATENCION
    ticket.atencion_inicio = ahora
    ticket.save(update_fields=["estado", "atencion_inicio"])
    _registrar(ticket, Tipo.ATENCION_INICIADA, ahora, funcionario=funcionario, puesto=ticket.puesto)
    return ticket


@transaction.atomic
def finalizar(ticket, funcionario):
    ticket = _bloquear(ticket, Estado.LLAMADO, Estado.EN_ATENCION)
    ahora = timezone.now()
    if ticket.atencion_inicio is None:
        ticket.atencion_inicio = ticket.llamado_en
    ticket.estado = Estado.FINALIZADO
    ticket.cerrado_en = ahora
    ticket.save(update_fields=["estado", "atencion_inicio", "cerrado_en"])
    _registrar(ticket, Tipo.FINALIZADO, ahora, funcionario=funcionario, puesto=ticket.puesto)
    return ticket


@transaction.atomic
def no_se_presento(ticket, funcionario):
    ticket = _bloquear(ticket, Estado.LLAMADO)
    ahora = timezone.now()
    ticket.estado = Estado.NO_SE_PRESENTO
    ticket.cerrado_en = ahora
    ticket.save(update_fields=["estado", "cerrado_en"])
    _registrar(ticket, Tipo.NO_SE_PRESENTO, ahora, funcionario=funcionario, puesto=ticket.puesto)
    return ticket


def _volver_a_espera(ticket, ahora):
    ticket.estado = Estado.EN_ESPERA
    ticket.puesto = None
    ticket.funcionario = None
    ticket.en_espera_desde = ahora
    ticket.llamado_en = None
    ticket.atencion_inicio = None
    ticket.veces_llamado = 0


@transaction.atomic
def derivar(ticket, servicio_destino, funcionario):
    """Envía el ticket a otro servicio de la misma unidad; conserva su código."""
    ticket = _bloquear(ticket, Estado.LLAMADO, Estado.EN_ATENCION)
    if servicio_destino.unidad_id != ticket.unidad_id or not servicio_destino.activo:
        raise OperacionInvalida("Solo se puede derivar a un servicio activo de la misma unidad.")
    if servicio_destino.pk == ticket.servicio_id:
        raise OperacionInvalida("El ticket ya está en ese servicio.")
    ahora = timezone.now()
    puesto = ticket.puesto
    # El evento queda asociado al servicio de origen.
    _registrar(ticket, Tipo.DERIVADO, ahora, funcionario=funcionario, puesto=puesto, servicio_destino=servicio_destino)
    _volver_a_espera(ticket, ahora)
    ticket.servicio = servicio_destino
    ticket.save()
    return ticket


@transaction.atomic
def reencolar(ticket, funcionario):
    """Devuelve el ticket llamado a la fila (p. ej. el paciente pidió esperar)."""
    ticket = _bloquear(ticket, Estado.LLAMADO)
    ahora = timezone.now()
    puesto = ticket.puesto
    _volver_a_espera(ticket, ahora)
    ticket.save()
    _registrar(ticket, Tipo.REENCOLADO, ahora, funcionario=funcionario, puesto=puesto)
    return ticket


@transaction.atomic
def cancelar(ticket, funcionario=None, motivo=""):
    ticket = _bloquear(ticket, *Ticket.ESTADOS_ACTIVOS)
    ahora = timezone.now()
    puesto = ticket.puesto
    ticket.estado = Estado.CANCELADO
    ticket.cerrado_en = ahora
    ticket.save(update_fields=["estado", "cerrado_en"])
    _registrar(ticket, Tipo.CANCELADO, ahora, funcionario=funcionario, puesto=puesto, motivo=motivo)
    return ticket
