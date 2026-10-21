# gestorfilas — contexto del proyecto

Gestor de filas de nivel empresarial para el **Hospital Dr. Gustavo Fricke (Viña del Mar)**,
desarrollado por el equipo de Integraciones / Unidad TIC. Reemplaza a **Debmedia**
(debQ 3.50, Scala/Play + AngularJS 1.5), que se cae con la carga actual.
Responder siempre en **español**.

- Repo oficial: Gitea interno `git@10.69.84.121:unidadtic/gestorfilas.git` (rama `main`).
- Espejo/respaldo: GitHub `MrRegom/gestordefilas` (remoto `github`).

## Objetivos
- Robusto: ~1.000 personas/día hoy, sin caídas; sin punto único de falla.
- Multi-unidad tipo SaaS: Farmacia, UGDA, OIRS, Odontología, Toma de Muestras, etc. se agregan
  por configuración, nunca por código. Escalable a más unidades/establecimientos.
- Pantallas TV en tiempo real (< 1 s) vía WebSockets; deben correr en **NUC antiguos**
  (HTML/CSS/JS puro, sin frameworks pesados, Chromium modo kiosko).
- Trazabilidad completa de funcionarios, pacientes atendidos y tiempos.
- Privacidad: el ticket NO imprime nombre ni RUT.

## Stack
Django 5.1 + DRF · PostgreSQL · (próximo) Django Channels + Redis · gunicorn/uvicorn ·
whitenoise · Docker Compose. Ver `docs/arquitectura.md`.

## Estructura
- `backend/` proyecto Django (`config/`, app `filas/`).
  - `filas/models.py`: Establecimiento → Unidad → SalaEspera, Servicio, Puesto, Totem, Pantalla;
    ContadorDiario (numeración por servicio y día, sin tarea nocturna); Ticket; EventoTicket
    (solo inserción, inmutable: base de la trazabilidad).
  - `filas/operaciones.py`: **única vía** para cambiar tickets (emitir, llamar_siguiente, rellamar,
    iniciar_atencion, finalizar, no_se_presento, derivar, reencolar, cancelar). Cada una valida la
    transición y registra el evento en la misma transacción. Orden de llamado: preferente →
    envejecido (espera ≥ minutos_envejecimiento) → prioridad del servicio → llegada.
    `select_for_update(skip_locked)` evita que dos puestos tomen el mismo ticket.
  - `filas/api_totem.py`: API del tótem autenticada con `Authorization: Totem <token>`
    (`/api/totem/config/`, `/api/totem/tickets/`, `/api/totem/latido/`).
  - `filas/templates/filas/totem.html`: pantalla táctil del tótem (`/totem/#TOKEN`).
  - `cargar_demo`: comando que crea una Farmacia de prueba e imprime la URL del tótem.
  - `filas/tests.py`: 20 pruebas (`python manage.py test filas`).
- `herramientas/agente_totem/`: agente local Python en cada tótem (127.0.0.1:8765) que recibe
  el ticket desde la pantalla y lo imprime; informa estado de impresora. `--simular` para pruebas.
- `herramientas/prueba_impresora/`: script de prueba inicial de impresión.
- `docs/`: `auditoria_debmedia_hgf.md` (auditoría funcional del sistema actual, ambiente de
  testing), `arquitectura.md` (plan por etapas), `despliegue.md` (Docker en servidor).

## Hardware de tótem (verificado)
- NUC con **Windows 11**, impresora térmica **"POS80 Printer"** (80 mm, ESC/POS, USB, driver Windows).
- Impresión **probada con éxito** enviando ESC/POS en modo RAW por el spooler con `pywin32`
  (`win32print`). Acentos/ñ OK con tabla PC850 (`ESC t 2`); QR OK (`GS ( k`); corte `GS V 66 0`.
- Texto doble ancho (`GS ! 0x11`) no cabe en 80 mm para títulos largos: usar doble alto (`0x01`).
- Pendiente verificar: lectura de estado (sin papel/tapa abierta) vía `GetPrinter` nivel 2.

## Avance (ver tabla en docs/arquitectura.md)
- ✅ Etapa 0: prueba de impresión POS80.
- ✅ Etapa 1: núcleo Django multi-unidad, tickets, eventos.
- ✅ Etapa 2: tótem + API con token + agente de impresión (E2E probado con impresión simulada).
- ✅ Docker Compose listo (no probado aún en servidor real).
- ⏭ **Etapa 3: puesto del funcionario** (llamar siguiente, re-llamar, atender, finalizar,
  no se presentó, derivar, re-encolar; fila en vivo). Usar `filas/operaciones.py`.
- Luego: 4 pantalla TV tiempo real con voz (Channels), 5 piloto, 6 supervisión/reportes Excel,
  7 panel de salud/pruebas de carga/HA, 8 integraciones (citas por RUT en 10.6.74.157:3000,
  prioridad Ley 21.168, WhatsApp/SMS, encuestas).

## Convenciones
- Código, modelos y textos en español; comentarios escasos y útiles.
- Nunca modificar tickets fuera de `operaciones.py`; nunca editar/borrar EventoTicket.
- Toda nueva funcionalidad con pruebas en `filas/tests.py`.
- Lecciones de Debmedia a evitar: polling cada 3 s, nombres de puesto duplicados en TV,
  RUT sin validar dígito verificador, demasiados administradores.
