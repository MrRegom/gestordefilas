"""API que consume la pantalla del tótem.

El tótem se identifica con su token (cabecera `Authorization: Totem <token>`),
sin usuario ni contraseña.
"""
from django.utils import timezone
from rest_framework import authentication, exceptions, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from . import operaciones as op
from .models import Ticket, Totem


class TotemAuthentication(authentication.BaseAuthentication):
    palabra = "Totem"

    def authenticate(self, request):
        partes = authentication.get_authorization_header(request).decode().split()
        if len(partes) != 2 or partes[0] != self.palabra:
            return None
        totem = Totem.objects.select_related("unidad__establecimiento").filter(token=partes[1], activo=True).first()
        if totem is None:
            raise exceptions.AuthenticationFailed("Tótem desconocido o deshabilitado.")
        Totem.objects.filter(pk=totem.pk).update(ultimo_contacto=timezone.now())
        return (None, totem)

    def authenticate_header(self, request):
        return self.palabra


class EsTotem(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, Totem)


class VistaTotem(APIView):
    authentication_classes = [TotemAuthentication]
    permission_classes = [EsTotem]


class ConfigTotem(VistaTotem):
    def get(self, request):
        totem = request.auth
        servicios = totem.servicios.filter(activo=True).order_by("prioridad", "nombre")
        return Response({
            "totem": totem.nombre,
            "impresora": totem.impresora,
            "unidad": totem.unidad.nombre,
            "establecimiento": totem.unidad.establecimiento.nombre,
            "servicios": [{"id": s.pk, "nombre": s.nombre, "letra": s.letra} for s in servicios],
        })


class SolicitudTicket(serializers.Serializer):
    servicio = serializers.IntegerField()
    preferente = serializers.BooleanField(default=False)


class EmitirTicketTotem(VistaTotem):
    def post(self, request):
        totem = request.auth
        datos = SolicitudTicket(data=request.data)
        datos.is_valid(raise_exception=True)
        servicio = totem.servicios.filter(pk=datos.validated_data["servicio"]).first()
        if servicio is None:
            raise exceptions.ValidationError({"servicio": "Este tótem no ofrece ese servicio."})
        try:
            ticket = op.emitir_ticket(servicio, totem=totem, preferente=datos.validated_data["preferente"])
        except op.OperacionInvalida as e:
            raise exceptions.ValidationError({"detalle": str(e)})

        delante = Ticket.objects.filter(
            servicio=servicio, fecha=ticket.fecha, estado=Ticket.Estado.EN_ESPERA, en_espera_desde__lt=ticket.en_espera_desde
        ).count()
        return Response({
            "id": ticket.pk,
            "codigo": ticket.codigo,
            "servicio": servicio.nombre,
            "unidad": totem.unidad.nombre,
            "establecimiento": totem.unidad.establecimiento.nombre,
            "preferente": ticket.preferente,
            "emitido_en": timezone.localtime(ticket.emitido_en).strftime("%d-%m-%Y %H:%M"),
            "personas_delante": delante,
            "impresora": totem.impresora,
        }, status=201)


class LatidoTotem(VistaTotem):
    """El tótem informa periódicamente que está vivo y el estado de su impresora."""

    def post(self, request):
        estado = str(request.data.get("estado_impresora", ""))[:100]
        Totem.objects.filter(pk=request.auth.pk).update(estado_impresora=estado, ultimo_contacto=timezone.now())
        return Response({"ok": True})
