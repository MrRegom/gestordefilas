from django.contrib import admin

from . import models


class EnUnidadAdmin(admin.ModelAdmin):
    list_filter = ["unidad__establecimiento", "unidad"]


@admin.register(models.Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "activo"]
    prepopulated_fields = {"codigo": ["nombre"]}


@admin.register(models.Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "establecimiento", "codigo", "activa"]
    list_filter = ["establecimiento", "activa"]
    prepopulated_fields = {"codigo": ["nombre"]}


@admin.register(models.SalaEspera)
class SalaEsperaAdmin(EnUnidadAdmin):
    list_display = ["nombre", "unidad", "activa"]


@admin.register(models.Servicio)
class ServicioAdmin(EnUnidadAdmin):
    list_display = ["letra", "nombre", "unidad", "sala", "prioridad", "minutos_envejecimiento", "activo"]
    list_editable = ["prioridad", "activo"]


@admin.register(models.Puesto)
class PuestoAdmin(EnUnidadAdmin):
    list_display = ["nombre", "nombre_pantalla", "unidad", "activo"]
    filter_horizontal = ["servicios"]


@admin.register(models.Totem)
class TotemAdmin(EnUnidadAdmin):
    list_display = ["nombre", "unidad", "impresora", "estado_impresora", "ultimo_contacto", "activo"]
    filter_horizontal = ["servicios"]
    readonly_fields = ["url_totem", "ultimo_contacto", "estado_impresora"]

    @admin.display(description="URL para abrir en el tótem")
    def url_totem(self, obj):
        return f"/totem/#{obj.token}" if obj.pk else "Se genera al guardar."


@admin.register(models.Pantalla)
class PantallaAdmin(EnUnidadAdmin):
    list_display = ["nombre", "unidad", "llamados_visibles", "voz", "activa"]
    filter_horizontal = ["servicios"]


class EventoTicketInline(admin.TabularInline):
    model = models.EventoTicket
    extra = 0
    can_delete = False
    readonly_fields = ["tipo", "momento", "servicio", "servicio_destino", "puesto", "funcionario", "datos"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(models.Ticket)
class TicketAdmin(admin.ModelAdmin):
    """Solo lectura: los tickets cambian únicamente a través de filas.operaciones."""

    list_display = ["codigo", "servicio", "unidad", "estado", "preferente", "puesto", "emitido_en"]
    list_filter = ["unidad", "estado", "preferente", "fecha"]
    search_fields = ["codigo"]
    date_hierarchy = "emitido_en"
    inlines = [EventoTicketInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
