from django.core.management.base import BaseCommand

from filas.models import Establecimiento, Pantalla, Puesto, SalaEspera, Servicio, Totem, Unidad


class Command(BaseCommand):
    help = "Crea datos de demostración (Farmacia del Hospital Fricke) para probar tótem, puestos y pantallas."

    def handle(self, *args, **options):
        hgf, _ = Establecimiento.objects.get_or_create(codigo="hgf", defaults={"nombre": "Hospital Dr. Gustavo Fricke"})
        farmacia, _ = Unidad.objects.get_or_create(establecimiento=hgf, codigo="farmacia", defaults={"nombre": "Farmacia"})
        sala, _ = SalaEspera.objects.get_or_create(unidad=farmacia, nombre="Sala Farmacia")
        servicios = []
        for letra, nombre, prioridad in [("M", "Entrega de medicamentos", 20), ("P", "Farmacia express", 15),
                                         ("Q", "Oncología", 10), ("L", "Anticoagulantes", 10)]:
            s, _ = Servicio.objects.get_or_create(unidad=farmacia, letra=letra,
                                                  defaults={"nombre": nombre, "prioridad": prioridad, "sala": sala})
            servicios.append(s)
        for i in range(1, 4):
            p, _ = Puesto.objects.get_or_create(unidad=farmacia, nombre=f"F-MOD {i:02d}",
                                                defaults={"nombre_pantalla": f"MÓDULO {i}"})
            p.servicios.set(servicios)
        totem, _ = Totem.objects.get_or_create(unidad=farmacia, nombre="Tótem Farmacia 1")
        totem.servicios.set(servicios)
        pantalla, _ = Pantalla.objects.get_or_create(unidad=farmacia, nombre="TV Farmacia 1")
        pantalla.servicios.set(servicios)
        self.stdout.write(self.style.SUCCESS(f"Listo. Tótem: /totem/#{totem.token}"))
