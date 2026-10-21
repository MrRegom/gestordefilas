"""Modelo de datos del gestor de filas.

Jerarquía multi-unidad:
    Establecimiento -> Unidad -> (SalaEspera, Servicio, Puesto, Totem, Pantalla)

Los tickets guardan su estado actual; cada cambio de estado queda además en
EventoTicket, que es de solo inserción y es la fuente de la trazabilidad.
"""
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Establecimiento(models.Model):
    nombre = models.CharField(max_length=150)
    codigo = models.SlugField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Unidad(models.Model):
    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.PROTECT, related_name="unidades")
    nombre = models.CharField(max_length=150)
    codigo = models.SlugField(max_length=50)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["establecimiento", "nombre"]
        verbose_name_plural = "unidades"
        constraints = [
            models.UniqueConstraint(fields=["establecimiento", "codigo"], name="unidad_codigo_unico"),
        ]

    def __str__(self):
        return self.nombre


class SalaEspera(models.Model):
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="salas")
    nombre = models.CharField(max_length=150)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["unidad", "nombre"]
        verbose_name = "sala de espera"
        verbose_name_plural = "salas de espera"

    def __str__(self):
        return f"{self.unidad} / {self.nombre}"


class Servicio(models.Model):
    """Una fila: tiene su letra y su correlativo diario."""

    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="servicios")
    sala = models.ForeignKey(SalaEspera, on_delete=models.PROTECT, related_name="servicios", null=True, blank=True)
    nombre = models.CharField(max_length=150)
    letra = models.CharField(max_length=3, help_text="Prefijo del número, p. ej. T o FX.")
    prioridad = models.PositiveSmallIntegerField(default=50, help_text="Menor número = se llama antes.")
    minutos_envejecimiento = models.PositiveSmallIntegerField(
        default=20, help_text="Tras esta espera el ticket pasa adelante de los servicios de menor prioridad."
    )
    numero_maximo = models.PositiveIntegerField(default=999, help_text="Al superarlo la numeración vuelve a 1.")
    max_tickets_dia = models.PositiveIntegerField(null=True, blank=True, help_text="Vacío = sin tope.")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["unidad", "prioridad", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["unidad", "letra"], name="servicio_letra_unica_por_unidad"),
        ]

    def __str__(self):
        return f"{self.letra} - {self.nombre}"

    def clean(self):
        if self.sala_id and self.sala.unidad_id != self.unidad_id:
            raise ValidationError({"sala": "La sala debe pertenecer a la misma unidad."})


class Puesto(models.Model):
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="puestos")
    nombre = models.CharField(max_length=100)
    nombre_pantalla = models.CharField(max_length=30, help_text="Lo que se anuncia en la TV, p. ej. MÓDULO 3.")
    servicios = models.ManyToManyField(Servicio, related_name="puestos", blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["unidad", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["unidad", "nombre_pantalla"], name="puesto_nombre_pantalla_unico"),
        ]

    def __str__(self):
        return f"{self.unidad} / {self.nombre}"


def generar_token():
    return secrets.token_urlsafe(32)


class Totem(models.Model):
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="totems")
    nombre = models.CharField(max_length=100)
    servicios = models.ManyToManyField(Servicio, related_name="totems", blank=True)
    impresora = models.CharField(max_length=100, default="POS80 Printer", help_text="Nombre de la impresora en Windows.")
    token = models.CharField(max_length=64, unique=True, default=generar_token, editable=False)
    activo = models.BooleanField(default=True)
    ultimo_contacto = models.DateTimeField(null=True, blank=True)
    estado_impresora = models.CharField(max_length=100, blank=True, help_text="Último estado informado por el agente.")

    class Meta:
        ordering = ["unidad", "nombre"]
        verbose_name = "tótem"
        verbose_name_plural = "tótems"

    def __str__(self):
        return f"{self.unidad} / {self.nombre}"


class Pantalla(models.Model):
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="pantallas")
    nombre = models.CharField(max_length=100)
    servicios = models.ManyToManyField(Servicio, related_name="pantallas", blank=True)
    llamados_visibles = models.PositiveSmallIntegerField(default=4)
    voz = models.BooleanField(default=True, help_text="Anunciar el llamado por voz.")
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["unidad", "nombre"]

    def __str__(self):
        return f"{self.unidad} / {self.nombre}"


class ContadorDiario(models.Model):
    """Correlativo por servicio y día. Un día nuevo parte de cero sin tarea nocturna."""

    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name="contadores")
    fecha = models.DateField()
    emitidos = models.PositiveIntegerField(default=0)
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["servicio", "fecha"], name="contador_servicio_fecha_unico"),
        ]


class Ticket(models.Model):
    class Estado(models.TextChoices):
        EN_ESPERA = "en_espera", "En espera"
        LLAMADO = "llamado", "Llamado"
        EN_ATENCION = "en_atencion", "En atención"
        FINALIZADO = "finalizado", "Finalizado"
        NO_SE_PRESENTO = "no_se_presento", "No se presentó"
        CANCELADO = "cancelado", "Cancelado"

    ESTADOS_ACTIVOS = (Estado.EN_ESPERA, Estado.LLAMADO, Estado.EN_ATENCION)

    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="tickets")
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="tickets")
    fecha = models.DateField(db_index=True)
    numero = models.PositiveIntegerField()
    codigo = models.CharField(max_length=10, help_text="Letra y número impresos, p. ej. T-015.")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EN_ESPERA, db_index=True)
    preferente = models.BooleanField(default=False, help_text="Atención preferente (Ley 21.168).")
    totem = models.ForeignKey(Totem, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    puesto = models.ForeignKey(Puesto, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets"
    )
    emitido_en = models.DateTimeField()
    en_espera_desde = models.DateTimeField(help_text="Se renueva al derivar o re-encolar.")
    llamado_en = models.DateTimeField(null=True, blank=True)
    atencion_inicio = models.DateTimeField(null=True, blank=True)
    cerrado_en = models.DateTimeField(null=True, blank=True)
    veces_llamado = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-emitido_en"]
        indexes = [models.Index(fields=["unidad", "estado", "fecha"])]

    def __str__(self):
        return self.codigo


class EventoTicket(models.Model):
    """Registro inmutable de todo lo que le pasa a un ticket."""

    class Tipo(models.TextChoices):
        EMITIDO = "emitido", "Emitido"
        LLAMADO = "llamado", "Llamado"
        RELLAMADO = "rellamado", "Re-llamado"
        ATENCION_INICIADA = "atencion_iniciada", "Atención iniciada"
        FINALIZADO = "finalizado", "Finalizado"
        NO_SE_PRESENTO = "no_se_presento", "No se presentó"
        DERIVADO = "derivado", "Derivado"
        REENCOLADO = "reencolado", "Re-encolado"
        CANCELADO = "cancelado", "Cancelado"

    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="eventos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    momento = models.DateTimeField(db_index=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="eventos")
    servicio_destino = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, null=True, blank=True, related_name="eventos_destino"
    )
    puesto = models.ForeignKey(Puesto, on_delete=models.PROTECT, null=True, blank=True, related_name="eventos")
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="eventos_ticket"
    )
    datos = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["momento", "id"]
        verbose_name = "evento de ticket"
        verbose_name_plural = "eventos de ticket"

    def __str__(self):
        return f"{self.ticket} {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Los eventos de ticket no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los eventos de ticket no se pueden eliminar.")
