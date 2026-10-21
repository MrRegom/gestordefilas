from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from . import operaciones as op
from .models import Establecimiento, EventoTicket, Puesto, Servicio, Ticket, Unidad

Estado = Ticket.Estado
Tipo = EventoTicket.Tipo


class BaseFilas(TestCase):
    def setUp(self):
        hgf = Establecimiento.objects.create(nombre="Hospital Dr. Gustavo Fricke", codigo="hgf")
        self.farmacia = Unidad.objects.create(establecimiento=hgf, nombre="Farmacia", codigo="farmacia")
        self.oirs = Unidad.objects.create(establecimiento=hgf, nombre="OIRS", codigo="oirs")
        self.medicamentos = Servicio.objects.create(unidad=self.farmacia, nombre="Entrega de medicamentos", letra="M", prioridad=20)
        self.preferencial = Servicio.objects.create(unidad=self.farmacia, nombre="Preferencial", letra="P", prioridad=10)
        self.puesto = Puesto.objects.create(unidad=self.farmacia, nombre="F-MOD 01", nombre_pantalla="MÓDULO 1")
        self.puesto.servicios.set([self.medicamentos, self.preferencial])
        self.funcionario = get_user_model().objects.create_user("qf1")


class EmisionTests(BaseFilas):
    def test_numeracion_correlativa_por_servicio(self):
        m1 = op.emitir_ticket(self.medicamentos)
        m2 = op.emitir_ticket(self.medicamentos)
        p1 = op.emitir_ticket(self.preferencial)
        self.assertEqual([m1.codigo, m2.codigo, p1.codigo], ["M-001", "M-002", "P-001"])
        self.assertEqual(m1.eventos.get().tipo, Tipo.EMITIDO)

    def test_numeracion_reinicia_al_dia_siguiente(self):
        op.emitir_ticket(self.medicamentos)
        manana = timezone.now() + timedelta(days=1)
        with mock.patch("django.utils.timezone.now", return_value=manana):
            self.assertEqual(op.emitir_ticket(self.medicamentos).codigo, "M-001")

    def test_numeracion_vuelve_a_uno_al_superar_maximo(self):
        self.medicamentos.numero_maximo = 2
        self.medicamentos.save()
        codigos = [op.emitir_ticket(self.medicamentos).codigo for _ in range(3)]
        self.assertEqual(codigos, ["M-1", "M-2", "M-1"])

    def test_tope_diario(self):
        self.medicamentos.max_tickets_dia = 1
        self.medicamentos.save()
        op.emitir_ticket(self.medicamentos)
        with self.assertRaises(op.OperacionInvalida):
            op.emitir_ticket(self.medicamentos)

    def test_servicio_inactivo_no_emite(self):
        self.medicamentos.activo = False
        self.medicamentos.save()
        with self.assertRaises(op.OperacionInvalida):
            op.emitir_ticket(self.medicamentos)


class LlamadoTests(BaseFilas):
    def test_orden_preferente_prioridad_y_llegada(self):
        m1 = op.emitir_ticket(self.medicamentos)
        p1 = op.emitir_ticket(self.preferencial)
        m2 = op.emitir_ticket(self.medicamentos, preferente=True)
        self.assertEqual(op.candidatos(self.puesto), [m2, p1, m1])

    def test_envejecimiento_adelanta_ticket(self):
        m1 = op.emitir_ticket(self.medicamentos)
        p1 = op.emitir_ticket(self.preferencial)
        despues = timezone.now() + timedelta(minutes=self.medicamentos.minutos_envejecimiento + 1)
        # Ambos envejecen: vuelve a mandar la prioridad.
        self.assertEqual(op.candidatos(self.puesto, despues), [p1, m1])
        Ticket.objects.filter(pk=p1.pk).update(en_espera_desde=despues)
        self.assertEqual(op.candidatos(self.puesto, despues), [m1, p1])

    def test_puesto_solo_llama_sus_servicios(self):
        otro = Servicio.objects.create(unidad=self.farmacia, nombre="Oncología", letra="Q", prioridad=1)
        op.emitir_ticket(otro)
        self.assertIsNone(op.llamar_siguiente(self.puesto, self.funcionario))

    def test_flujo_completo_registra_eventos(self):
        t = op.emitir_ticket(self.medicamentos)
        t = op.llamar_siguiente(self.puesto, self.funcionario)
        op.rellamar(t, self.funcionario)
        op.iniciar_atencion(t, self.funcionario)
        t = op.finalizar(t, self.funcionario)
        self.assertEqual(t.estado, Estado.FINALIZADO)
        self.assertEqual(t.veces_llamado, 2)
        self.assertEqual(
            list(t.eventos.values_list("tipo", flat=True)),
            [Tipo.EMITIDO, Tipo.LLAMADO, Tipo.RELLAMADO, Tipo.ATENCION_INICIADA, Tipo.FINALIZADO],
        )
        self.assertTrue(all(e.puesto == self.puesto for e in t.eventos.exclude(tipo=Tipo.EMITIDO)))

    def test_llamar_siguiente_cierra_el_actual(self):
        a = op.emitir_ticket(self.medicamentos)
        b = op.emitir_ticket(self.medicamentos)
        op.llamar_siguiente(self.puesto, self.funcionario)
        siguiente = op.llamar_siguiente(self.puesto, self.funcionario)
        a.refresh_from_db()
        self.assertEqual(a.estado, Estado.NO_SE_PRESENTO)
        self.assertEqual(siguiente, b)

    def test_transicion_invalida(self):
        t = op.emitir_ticket(self.medicamentos)
        with self.assertRaises(op.OperacionInvalida):
            op.finalizar(t, self.funcionario)

    def test_derivar_mantiene_codigo_y_vuelve_a_espera(self):
        op.emitir_ticket(self.medicamentos)
        t = op.llamar_siguiente(self.puesto, self.funcionario)
        t = op.derivar(t, self.preferencial, self.funcionario)
        self.assertEqual((t.codigo, t.servicio, t.estado, t.puesto), ("M-001", self.preferencial, Estado.EN_ESPERA, None))
        evento = t.eventos.get(tipo=Tipo.DERIVADO)
        self.assertEqual((evento.servicio, evento.servicio_destino), (self.medicamentos, self.preferencial))

    def test_no_deriva_a_otra_unidad(self):
        consulta = Servicio.objects.create(unidad=self.oirs, nombre="Consultas", letra="A")
        op.emitir_ticket(self.medicamentos)
        t = op.llamar_siguiente(self.puesto, self.funcionario)
        with self.assertRaises(op.OperacionInvalida):
            op.derivar(t, consulta, self.funcionario)


class EventoInmutableTests(BaseFilas):
    def test_evento_no_se_modifica_ni_elimina(self):
        evento = op.emitir_ticket(self.medicamentos).eventos.get()
        with self.assertRaises(ValidationError):
            evento.save()
        with self.assertRaises(ValidationError):
            evento.delete()


class ApiTotemTests(BaseFilas):
    def setUp(self):
        super().setUp()
        from .models import Totem

        self.totem = Totem.objects.create(unidad=self.farmacia, nombre="Tótem 1")
        self.totem.servicios.set([self.medicamentos])
        self.auth = {"HTTP_AUTHORIZATION": f"Totem {self.totem.token}"}

    def test_sin_token_rechaza(self):
        self.assertEqual(self.client.get("/api/totem/config/").status_code, 401)
        r = self.client.get("/api/totem/config/", HTTP_AUTHORIZATION="Totem malo")
        self.assertEqual(r.status_code, 401)

    def test_config_lista_solo_servicios_del_totem(self):
        r = self.client.get("/api/totem/config/", **self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([s["letra"] for s in r.json()["servicios"]], ["M"])
        self.totem.refresh_from_db()
        self.assertIsNotNone(self.totem.ultimo_contacto)

    def test_emitir_ticket(self):
        op.emitir_ticket(self.medicamentos)
        r = self.client.post("/api/totem/tickets/", {"servicio": self.medicamentos.pk, "preferente": True},
                             content_type="application/json", **self.auth)
        self.assertEqual(r.status_code, 201)
        datos = r.json()
        self.assertEqual((datos["codigo"], datos["preferente"], datos["personas_delante"]), ("M-002", True, 1))
        self.assertEqual(Ticket.objects.get(pk=datos["id"]).totem, self.totem)

    def test_no_emite_servicio_ajeno(self):
        r = self.client.post("/api/totem/tickets/", {"servicio": self.preferencial.pk},
                             content_type="application/json", **self.auth)
        self.assertEqual(r.status_code, 400)

    def test_latido_guarda_estado_impresora(self):
        r = self.client.post("/api/totem/latido/", {"estado_impresora": "sin papel"},
                             content_type="application/json", **self.auth)
        self.assertEqual(r.status_code, 200)
        self.totem.refresh_from_db()
        self.assertEqual(self.totem.estado_impresora, "sin papel")

    def test_pagina_totem(self):
        self.assertContains(self.client.get("/totem/"), "Toque el servicio")
