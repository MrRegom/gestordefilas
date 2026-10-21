# Auditoría funcional: Debmedia (gestor de filas) del Hospital Dr. Gustavo Fricke

**Fecha de revisión:** 21-10-2026 (entre 12:10 y 12:40 aprox.)
**Instancia:** `http://10.6.74.159/` (red interna). Sucursal "informatica" (id 2), compañía "hgf" (id 2)
**Usuario de revisión:** perfil *Administrator* de sucursal
**Método:** revisión **solo de lectura**. Recorrí los menús, abrí los formularios de edición sin guardar (salí con *Volver* o *Cancelar*) y consulté por GET la misma API REST que usa la interfaz. No se emitieron, llamaron, editaron ni eliminaron turnos o registros. No abrí los puestos de "Puestos de atención", porque entrar a uno conecta al usuario a ese puesto y cambia su estado.
**Anonimización:** no se copiaron RUT, nombres, teléfonos ni correos de pacientes. Los nombres de funcionarios se reemplazaron por `[FUNCIONARIO]` y no se copiaron contraseñas ni tokens.

> ⚠️ **Hallazgo principal:** el sistema está **casi en desuso**. De 51 trámites, solo 5 están habilitados (Toma de Muestras ×3, CAE y OIRS). Las salas de Admisión, Farmacia y Hospitalización, 15 de 20 kioscos y la mayoría de los trámites se deshabilitaron el **20-01-2025**. Los reportes muestran **0 ingresos en 2025 y 2026** (solo 1 atención en 2026). Hoy, miércoles a mediodía, había 0/69 puestos conectados y 0 turnos en espera. La única tarea que sigue corriendo es el reinicio nocturno de filas. Por eso, la mayor parte de este informe describe **la configuración heredada** (de 2024 y antes), que es la referencia útil para el sistema nuevo.

---

## 1. Mapa del sistema

Debmedia está formado por tres productos que comparten la misma interfaz web (AngularJS, menú lateral):

- **debQ** (gestor de filas)
- **debSign** (cartelería digital: pantallas y kioscos)
- **debPlayer** (reproductor en los dispositivos)

En el encabezado hay un selector "Sistema debQ / Sistema debSign", el selector de sucursal ("Informatica"), un ícono ⓘ con la información de versión y *Log out*.

| Menú | Submenú / pantalla | Para qué sirve |
|---|---|---|
| **Panel de sucursal** | (inicio) Dashboard | Muestra KPIs en tiempo real: puestos online (0/69), TVs online (10/15), kioscos online (4/9), nivel de servicio, promedio de espera y de atención, turnos en espera y en atención. Incluye tablas por puesto, trámite, pantalla, kiosco y perfil, y una bitácora de "Mensajes del sistema" con filtro de fechas y exportación. Tiene modo de refresco Manual o Automático (cada N segundos), ítems por página y vista por Hora o Día. Botón "Exportar HTML". |
| | Usuarios | ABM de usuarios (email, nombre, apellido, perfil/rol, puestos habilitados). 151 usuarios en 16 páginas. |
| | Puestos | ABM de puestos o módulos: nombre, nombre en pantalla (TV), salas de espera atendibles, ubicación, perfil de puesto y "próximo perfil". Se pueden habilitar y deshabilitar. |
| | Trámites | ABM de trámites (filas): sala por defecto, máximo de turnos por día, tipo (encolable o no), numeración, alertas y prioridad. Desde aquí hay un botón para **emitir turno** (`queueUp`), que no usé. |
| | Grupos de trámites | Agrupa trámites para el llamado: prioridad, tipo de grupo (Normal / Pre trámite / Llamado directo / Desborde), alertas y tamaño del buffer. |
| | Salas de espera | ABM de salas (solo ID y nombre). |
| | Multimedias | Carpetas y archivos (imágenes y videos) usados en pantallas, kioscos y tickets. |
| | Pantallas | TVs "turnero": trámites que muestra cada una, turnero por URL (con token), edición de publicidad o plantilla y "Limpiar pantalla". |
| | Kioscos | Tótems: trámites asignados y un editor de diapositivas interactivas (flujo del tótem). |
| | Perfiles de Puestos | Plantillas de comportamiento del puesto: botones habilitados, algoritmo de llamado, trámites que atiende y de derivación, estados del puesto y alertas. |
| **Avanzada** | Tareas | Tareas programadas. Solo existe "Reinicio de filas" (cada 1440 min). |
| | Configuraciones | Parámetros globales: numeración, tickets masivos, sincronismo, mail, citas externas, servicios web, etc. |
| **CRM** | Clientes | Base de pacientes ("clientes"): DNI/RUT, cédula, nombre, CUIT, razón social y tipo de cliente. **250.752 registros.** |
| | Tipos de cliente | "No cliente" (base) y "Cliente". |
| **Monitoreo** | Monitoreo sucursal | Equivale al dashboard del Panel de sucursal. |
| | Monitoreo de kioscos | Kioscos online y offline, errores y alertas de **impresoras** por terminal. |
| | Monitoreo salas de espera | KPIs filtrados por sala, con los puestos de esa sala y su estado. |
| | Monitoreo de turnos | Lista en vivo de turnos (en espera, en atención, ausentados) con filtros y columnas configurables. |
| **Analítica y datos** | Auditoría | Registro de acciones de usuarios (login y logout, cambios de configuración, ABM). |
| | Reportes | Reporte consolidado por día, mes o año, con exportación de tablas. |
| | Estadísticas | Gráficos por Región, Sucursal, Trámites, Usuarios, Estados, Tipo de cliente y Sala de espera. Exporta a Excel 2007 y PDF. |
| | Movimientos | Detalle de cada evento de cada turno. Exporta a Excel y PDF. |
| | Comparación de estadísticas | Compara dos periodos por sucursal, usuario, trámite, tipo de cliente, sala, subtrámite o usuario×trámite. |
| **Puestos de atención** | Lista de puestos (unos 41 visibles) | Accesos directos a la **consola del funcionario** de cada puesto. No la abrí. |

---

## 2. Servicios / filas (Trámites)

**Modo de numeración:** "Numeración por trámite" (`QUEUE_NUMERATION`), es decir, cada trámite tiene su propio correlativo. Hay 84 rangos de numeración definidos y ninguno es compartido. El reinicio es diario (ver sección 10).

### 2.1 Trámites habilitados hoy (5)

| ID | Trámite | Prefijo / rango | Sala de espera | Prioridad (orden) | Espera para atención preferente |
|---|---|---|---|---|---|
| 8 | Toma De Muestras General | **T** 0–9999 | Sala de espera Toma de Muestras | 18 | 20 min |
| 9 | Toma De Muestras Infectología | **J** 0–9999 | Sala de espera Toma de Muestras | 19 | 20 min |
| 10 | Toma De Muestras Diabetes | **K** 0–9999 | Sala de espera Toma de Muestras | 20 | 20 min |
| 13 | CAE | **Z** 0–9999 | CAE (⚠️ esa sala está deshabilitada) | 23 | 20 min |
| 51 | Oirs | **A** 1–999 | OIRS | 10 | 20 min |

### 2.2 Trámites heredados (deshabilitados, la mayoría el 20-01-2025)

| ID | Trámite | Prefijo | Sala | Prioridad | Notas |
|---|---|---|---|---|---|
| 1 | Hospitalización | H 0–9999 | Hospitalización | 12 | |
| 2 | Preferencial | A 0–9999 | Admisión | **0 (máxima)** | Espera preferente de 3 min |
| 3 | Entrega de Citaciones | C 0–9999 | Admisión | 14 | |
| 4 | Admisión General | D 0–9999 | Admisión | 16 | Alertas distintas (5;30 espera y 15;50 total) |
| 5 | Auge | E 0–9999 | Admisión | 13 | Espera preferente de 3 min |
| 6 | Atención express | B 0–9999 | Admisión | 15 | Espera preferente de 15 min |
| 7 | Entrega De Medicamentos | M 0–999 | Farmacia | 17 | Tope de 10.000 turnos/día y alertas en 99 (desactivadas en la práctica) |
| 11 | Farmacia Express | P 0–9999 | Farmacia | 21 | |
| 12 | Preferencial Farmacia | O 0–9999 | Farmacia | 22 | |
| 14 | Prequirúrgico | F 0–9999 | Hospitalización | 24 | |
| 15 | H - Informaciones | G 0–9999 | Hospitalización | 26 | |
| 16 | Oncología | Q 0–9999 | Farmacia | 25 | |
| 17 | Anticoagulantes | L 1–9999 | Farmacia | 30 | Espera preferente de 1 min |
| 18 | AGENDA TM | TM 1–9999 | Admisión | 27 | |
| 19 | MÓDULO DE TURNO | MT 1–999 | Admisión | 28 | |
| 20–25 | Farmacia - A, B, C, D, E, F | A–F 0–99 | Farmacia / Hosp. | 33–40 | Parecen pruebas |
| 26–40, 42–50, 41 | "Trámite 1…40", "anticoagulantes1" | Z, `[`, `\`, `]`, `^`, `_`, `` ` ``, a–h, A | Hospitalización | 1–46 | **Basura de pruebas**: prefijos con caracteres no alfabéticos |

**Atributos que tiene cada trámite:** nombre, sala de espera por defecto, máximo de turnos por día (vacío = sin tope), tipo (*Encolable* / *No encolable con ticket* / *No encolable sin ticket*), "Balancear salas de espera", "Computa nivel de servicio", "Encolar desde API externa", descripción, numeración y 4 alertas (tiempo de espera, tiempo de atención, tiempo total y clientes en espera). Ningún trámite usa atención virtual ni encolado externo.

**Horarios:** no hay horario a nivel de trámite. Los horarios se definen en **cada botón del tótem** ("días activos" e "intervalos activos"), y en todos los botones están configurados como **Lun–Dom, 00:00–23:59**.

---

## 3. Puestos / módulos / escritorios

Hay **69 puestos definidos** (0 conectados al momento de la revisión). La consola de cada puesto ofrece los trámites que define su **perfil de puesto**. Además, el puesto tiene "Salas de espera atendibles" y un "Nombre en pantalla", que es lo que se anuncia en la TV.

| Grupo | Puestos | Nombre en TV | Perfil asignado | Sala | Algoritmo |
|---|---|---|---|---|---|
| Admisión | A - MOD 01 a A - MOD 09 | MOD 1…MOD 9 | ADM - MOD 3 | Admisión | Envejecimiento por trámite |
| | A - MOD 10, A - MOD 11 | MOD 10, MOD 11 | ADM - MOD 11 | Admisión | Envejecimiento por trámite |
| | A - MOD 00 | **MOD 8** (⚠️ repite el de A-MOD 08) | Jefatura UGAA | Admisión | |
| Farmacia | F - MOD 01, 02 | MOD 1, 2 | Farmacia - O y M | Farmacia | Envejecimiento |
| | F - MOD 03 | MOD 3 | Farmacia P - M | Farmacia | Prioridad por trámite |
| | F - MOD 04, 05, 06 | MOD 4–6 | Farmacia - SOLO M | Farmacia | Envejecimiento |
| | F - MOD 07, 08, 09 | MOD 7–9 | Farmacia - Q y L | Farmacia | Prioridad por trámite |
| | F - MOD 00 | MOD 0 | Jefatura F | Farmacia | |
| | F - MOD 30 | **MOD 40** | Farmacia - SOLO M | Farmacia | |
| | 5 puestos de químicos farmacéuticos (nombre de persona) | "QF [FUNCIONARIO]" | Jefatura F | Farmacia | |
| | Monitoreo Farmacia 1, 2 y 3 | — | Monitoreo Farmacia | Farmacia | Orden de llegada, sin botones |
| Hospitalización | H - MOD 16 | **MOD 18** (⚠️ repite el de H-MOD 18) | Hosp - H | Hospitalización | Envejecimiento |
| | H - MOD 17, 18 | MOD 17, 18 | Hosp - H | Hospitalización | |
| | H - MOD 19, 20 | MOD 19, 20 | Hosp - F y H | Hospitalización | |
| | Box 49 a Box 69 (21 puestos) | Box NN | H - MOD 16 | Hospitalización | Prioridad por trámite |
| Toma de Muestras | TM - General | TM - General | TM - General | Toma de Muestras | Prioridad por trámite |
| | TM - Diabetes | MOD 2 | TM - Diabetes | Toma de Muestras | |
| | TM - Infectología | MOD 1 | **TM - Trasplantados** (⚠️ nombre cruzado) | Toma de Muestras | |
| | TM - Trasplantados | MOD 3 | TM - Trasplantados | Toma de Muestras | |
| Jefaturas y monitoreo | Jefatura UGAA, Jefatura Hospitalización, Jefatura SDGU, Monitoreo Admisión, Monitoreo UGAA, 1 puesto con nombre de persona | — | Perfiles de jefatura | varias | Solo Ausente y Buscar turno |
| Comodín | "Todas las Filas" | — | Administrador | Hospitalización | Todos los botones |

### Perfiles de puesto y trámites que atienden

Hay 36 perfiles. Solo **4 perfiles** tienen trámites o grupos asignados *hoy*, porque al deshabilitar los trámites quedaron vacíos:

- **TM** → grupo "Toma de muestras"
- **TM - Diabetes** → Toma De Muestras Diabetes
- **TM - Trasplantados** → Toma De Muestras Infectología
- **TM - General** → Toma De Muestras General
- **Todas las Filas** → TM General, Infectología, Diabetes, CAE y los grupos Hospitalización, Admisión, Farmacia, Toma de muestras y Todas

Los nombres de los perfiles heredados indican qué atendía cada puesto según la letra: "Farmacia - O y M" (Preferencial Farmacia y Medicamentos), "SOLO M", "Q y L" (Oncología y Anticoagulantes), "Admisión - A B D" (Preferencial, Express, Admisión General), "Hosp - F y H" (Prequirúrgico y Hospitalización), etc.

---

## 4. Usuarios y roles

**151 usuarios** en la sucursal:

| Rol (perfil de sistema) | Cantidad | Permisos observados / inferidos |
|---|---|---|
| `administrator` (Admin de sucursal) | **30** | Acceso total al panel de sucursal: ABM, configuraciones, analítica y CRM. Pueden modificar perfiles (`isAbleToModifiyProfiles = true`). |
| `workstation` (Puesto de atención) | 119 | Solo usan la consola del puesto o puestos asignados. |
| `monitor` | 1 | Monitoreo en vivo, sin operar turnos. |
| `Jefe sección` (perfil personalizado) | 1 | Supervisión. |
| Otros perfiles existentes sin usuarios en la sucursal | — | `designer` y `editor` (debSign: diseño de contenidos), `publisher` (publicar contenidos), `receptionist` (recepción: emitir turnos manualmente), `administrador compañía debsign`. |

- **Puestos asignados por usuario:** 9 usuarios sin puestos, 13 con 1, 16 con 2–5, 112 con 6–20 y 1 con más de 20. Muchos usuarios pueden entrar a muchos puestos.
- **"Fila visible" (`queueVisible`):** 109 usuarios ven la fila en su consola y 42 no.
- La sucursal tiene restringidas algunas APIs, como `numerationModes` y `configs/branch`, que responden 403 o *Unauthorized*. Esas configuraciones dependen del administrador de compañía (Debmedia).

---

## 5. Tótems (Kioscos)

### 5.1 Inventario

| Kiosco (player) | Estado | Trámites asignados | Contenido |
|---|---|---|---|
| Kiosco 6 (11) | Habilitado | 20 trámites (todos los heredados) | **Int Pad Alfanumérico(1)**, el flujo interactivo |
| Kiosco 12–18 (27–33) | Habilitados | Hospitalización, Preferencial, Entrega de Citaciones | **Turnero V2** (⚠️ es una plantilla de TV, no de tótem) |
| Kiosco 19 (34) | Habilitado | Hospitalización, Preferencial, Entrega de Citaciones | Int Pad Alfanumérico(1) |
| Kiosco 1 (×5, players 6–10), Kiosco 7–11 | Deshabilitados (2017–2025) | | |

El monitoreo indica **4 kioscos online y 5 offline, 1 kiosco con error y 1 impresora con error**. El último mensaje del sistema sobre impresoras es "Impresora desconectado" (04-04-2026).

### 5.2 Flujo del tótem (publicidad interactiva "Int Pad Alfanumérico")

Pantalla vertical **1080×1920 (9:16)** con imágenes de fondo propias (RUT.jpg, TRAMITES.jpg y botones "Continuar", "Volver" y "Saltar").

1. **RUT:** teclado (keypad) para ingresar el identificador. El tipo de dato está configurado como "DNI", que en la práctica es el RUT. Tiene un botón **Saltar**, así que el RUT es **opcional**.
   - Al ingresarlo, consulta el CRM externo (`/api/terminal/customerTypeByExternalCRM/...`) y hace un **cambio condicional** según el tipo de cliente (No cliente, Cliente o Múltiple). Hoy las tres ramas llevan a "DATOS CLIENTE".
   - "Autocompletado de clientes" está desactivado.
2. **DATOS CLIENTE:** muestra los datos del paciente, con botones **CONTINUAR** (va a TRÁMITES) y **VOLVER** (va a RUT).
3. **TRÁMITES (menú principal):** botones **OIRS** (⚠️ emite turno del trámite **CAE**), **Toma de Muestra** (abre un submenú) y **Volver**.
4. **Submenús:**
   - **ADMISIÓN:** Preferencial, Admisión General, Atención express, Entrega de Citaciones, Módulo Turno y Volver.
   - **TOMA DE MUESTRAS:** General, Infectología, Diabetes y Volver.
   - **HOSPITALIZACIÓN:** Hospitalización, Pre Quirúrgico y Volver.
   - **FARMACIA:** Preferencial, Entrega de Medicamentos, Oncología, Anticoagulantes, Farmacia Express, "A" y Volver.

   Hoy los submenús Admisión, Hospitalización y Farmacia no son accesibles desde el menú principal (huérfanos).
5. Cada botón de trámite tiene la acción "Seleccionar trámite y finalizar", que emite el turno (`/api/terminal/queueUp`), imprime el ticket y vuelve al inicio. Cada botón tiene días y horario activos, pero todos están en 24/7.

Otras características del tótem:

- **Idioma:** solo español. No hay selector de idioma.
- **Accesibilidad:** no hay opciones de accesibilidad (audio, alto contraste o tamaño de letra). Existe la fuente de numeración `REDUCED_MOBILITY_NUMERATION` (movilidad reducida), pero no es accesible con este rol. La atención preferente se resuelve con botones "Preferencial" separados.
- **Tickets masivos:** deshabilitados (máximo 0).
- **Máximo de turnos por cliente y trámite:** 0 (sin límite).

### 5.3 Diseño del ticket

Hay 6 plantillas. La que corresponde al hospital es **"TICKET CON LOGO"**, y existe otra similar sin logo ("Template 1 suc 1"):

1. Logo (LOGO FRICKE / logoticket.png)
2. Separador
3. **Número de turno** (letra y número, tamaño 40)
4. Nombre del trámite
5. "Ticket intransferible"
6. **Nombre completo del paciente**
7. Campos adicionales
8. **DNI/RUT del paciente**
9. Separador
10. "www.hospitalfricke.cl"
11. Fecha y hora
12. "Ticket válido solo por hoy"

Las plantillas genéricas también permiten imprimir personas en espera (`standBy`), tiempo estimado de espera, sala de espera, código móvil, CUIT o razón social, encabezados y pie. La "Publicidad de ticket" está desactivada.

> Nota de privacidad para el sistema nuevo: el ticket actual **imprime el nombre y el RUT del paciente**.

---

## 6. Pantallas TV

Hay 15 pantallas. Cada una tiene un *Player ID*, la lista de trámites que muestra, "Turnero en URL" (habilitado o no, con token regenerable), "Edición de publicidad" (plantilla debSign) y "Limpiar pantalla".

| Pantalla | Turnero URL | Trámites mostrados |
|---|---|---|
| Pantalla 1, 2, 3 | Sí | Admisión: Preferencial, Citaciones, Admisión General, Express, Módulo de turno (la 2 también AGENDA TM y la 3 también Auge) |
| Pantalla 4 | Sí | Hospitalización |
| Pantalla 5, Farmacia 2, Pantalla 7 | Sí | Farmacia: Medicamentos, Express, Preferencial, Oncología, Anticoagulantes, (Farmacia-A) |
| **Pantalla 8, 9** | Sí | **Toma de Muestras General, Infectología y Diabetes** (las únicas con trámites activos) |
| Pantalla 10–14 | No | Hospitalización, Preferencial, Citaciones |
| Pantalla 15 | No | 16 trámites |

En el dashboard aparecen **10 de 15 TVs online**.

**Diseño "Turnero V2"** (1920×1080, 16:9):

- Tabla de turnos con **4 entradas** (los últimos llamados), con columnas Turno y Puesto. Encabezado azul #253E77, fuente Open Sans y número grande (160 px).
- El último llamado **parpadea** (efecto *blink*).
- En la parte inferior hay una franja de texto deslizante horizontal (carousel), actualmente vacía.
- Existen fondos de marca (HGFPantallaHorizontal.png y HGFPantallVertical.png) y contenidos de publicidad en debSign ("HGF - TV", "Player Default", video "Logo debmedia.mp4").

**Comportamiento de los turnos en pantalla:** "En orden de llamado". La alternativa era "Mantener último por trámite".

**Voz:** la opción **"Llamado por voz" está desactivada**. El llamado se anuncia solo visualmente, con parpadeo; no se encontró configuración de "ding" o sonido aparte. El puesto tiene la opción "Llamado silencioso", también desactivada.

**Publicidad:** se gestiona en debSign mediante canales 2.1, 2.2, 2.3, … con:

- sincronización continua cada 2 min
- ventana de sincronización 22:00–06:00
- 15 días de contenido y 15 días de retención de medios
- comportamiento definido ante desconexión o falta de publicidad

En las pantallas activas no hay videos de publicidad cargados.

---

## 7. Flujo de atención del funcionario

### 7.1 Estados del turno

Los deduje de Monitoreo, Estadísticas, Reportes y Movimientos:

| Estado / evento | Dónde aparece |
|---|---|
| **Ingreso / Emitido (En espera)** | "Turnos en espera", "Ingresos" |
| **Llamado** | consola (botón Llamar) |
| **Re-llamado** | botón "Volver a llamar" |
| **En atención** | "Turnos en atención" |
| **Finalizado** | "Finalizados", "Total de atenciones" |
| **No se presentó / Ausentado** | "No se presentó", "Ausentado", "Abandonos" |
| **Derivado** | "Derivados", "Ingresos derivados" (hacia otro trámite o usuario) |
| **Re-encolado** | botón "Re-encolar" (vuelve a la fila) |
| **Llamado cancelado** | botón "Cancelar llamado" (vuelve a espera) |
| **Ingreso externo / Cancelado externo** | turnos creados o anulados por API externa |
| **Desdoblado** (unfold: llamado o finalizado) | función desactivada |
| "Sin estadísticas" | movimientos que superan el "tiempo máximo admisible de estadísticas" no se computan |

### 7.2 Estados del puesto (funcionario)

Los estados son **Conectado - Disponible**, **Conectado - En atención**, **Ausente** y **Desconectado**. El estado inicial es configurable por perfil (Admisión: Conectado - Disponible). Tras **29–30 min de inactividad** el puesto pasa automáticamente a *Ausente*; en ADM-MOD 10 y 11 el umbral es de 10 min.

### 7.3 Botones / acciones disponibles

Se habilitan por perfil. Entre paréntesis, cuántos de los 69 puestos los tienen activos:

| Acción | Puestos | Comentario |
|---|---|---|
| **Llamar** | 34 | |
| **Llamar siguiente** | 52 | Finaliza el actual y llama al próximo |
| **Finalizar** | 59 | |
| **No se presentó** | 52 | Internamente `revoke` |
| **Volver a llamar** | 52 | |
| **Ausente** | 63 | Pausa del puesto |
| **Re-encolar** | 16 | |
| **Derivar** | 27 | Con "Trámites de derivación"; derivación a usuario específico desactivada |
| **Cancelar llamado** / **Cancelar derivación** | 2 | |
| **Buscar turno** | 57 | |
| **Elegir turno** | 15 | Atender uno fuera de orden |
| Llamado directo, Tipificar, Imprimir ticket en el puesto, Atender pre-trámite, Buscar perdidos, Desdoblar, Derivar con prioridad | 0 | Disponibles pero desactivados |

**Otras opciones por perfil:**

- **Llamado automático:** desactivado en todos (si estuviera activo: modo STATIC_SIZE o BALANCED, demora de 60 s).
- **Notificar nuevo turno:** sí, con duración fija.
- **Mensaje de finalización y de derivación:** desactivados.
- **Mínimo tiempo para finalizar:** 0 s.
- **No recibe desborde / No atiende prioridad / Detalles de encolados:** desactivados.
- **Identificador en el puesto:** "Letra y número". La alternativa es "Nombre y apellido".
- **Sincronismo puesto–servidor:** Asincrónico (*polling* cada 3000 ms). La alternativa es WebSocket.

---

## 8. Reglas de prioridad y atención preferente

1. **Algoritmo de llamado (por perfil de puesto).** Hay 7 opciones:
   - Orden de llegada (3 puestos)
   - **Prioridad por trámite** (29 puestos)
   - Prioridad por cliente
   - Prioridad por trámite y cliente
   - **Envejecimiento por trámite** (37 puestos)
   - Envejecimiento por cliente
   - Envejecimiento por trámite y cliente
2. **Prioridad del trámite:** es un número donde menor = más prioritario. *Preferencial* tiene 0, Hospitalización 12, Auge 13, Citaciones 14, Express 15, Admisión General 16, Medicamentos 17, TM 18–20, etc. Los grupos también tienen prioridad (29–57).
3. **Envejecimiento (aging):** con "Espera para prioridad" (`priorityWaitingTime`), un turno que lleva N minutos esperando sube de prioridad. Valores:
   - Preferencial y Auge: 3 min
   - Anticoagulantes: 1 min
   - Atención express: 15 min
   - Resto: 20 min
4. **Tipo de cliente:** "No cliente" tiene 20 min de espera para prioridad y multiplicador de envejecimiento 1. "Cliente" se determina por el CRM externo a partir del RUT ingresado.
5. **Atención preferente** (adultos mayores, embarazadas, discapacidad): **no hay un mecanismo explícito**. Se resuelve con trámites separados ("Preferencial", "Preferencial Farmacia") que el paciente elige en el tótem. "Habilitar escape" (permitir saltarse la prioridad) está activo en 25 puestos.
6. **Grupos de tipo Desborde, Pre-trámite y Llamado directo:** existen como opción pero no se usan. Todos los grupos son "Normal" o MULTI_QUEUES, con buffer de 3.

---

## 9. Reportes y estadísticas

| Módulo | Contenido / métricas | Filtros | Exportación |
|---|---|---|---|
| **Reportes** | Nivel de servicio (%); total de trámites y usuarios; máximos y mínimos (trámite con mayor y menor espera, usuario con más y menos atenciones); flujo (ingresos, atenciones, abandonos); tiempos (promedio de espera, de atención y de permanencia); gráfico de ingresos y atenciones por trámite; tabla de atenciones por usuario (nombre, atenciones, promedio de atención); tabla por sala de espera (ingresos, atenciones, abandonos, derivados, ingresos derivados, promedio de espera, de atención y de servicio) | Fecha inicial y final; Día, Mes o Año; sucursal | "Exportar tablas" |
| **Estadísticas** | Pestañas Región, Sucursal, Trámites, Usuarios, Estados, Tipo de cliente y Sala de espera. Gráficos de nivel de servicio, ingresos, finalizados, no se presentó, ingreso externo, cancelado externo, tiempo de espera y tiempo de atención | Hora, Día, Mes o Año; fecha; selección múltiple de entidad; "Graficar" | **Excel 2007, PDF** |
| **Movimientos** | Id de turno, turno, sucursal, acción, trámite, nombre en el puesto, email del usuario, fecha, hora, tags, tiempo de espera y tiempo de atención | Fechas, turno, sucursal, acción, trámite y email del usuario; columnas visibles configurables | **Excel, PDF** |
| **Comparación de estadísticas** | Compara periodos por sucursales, usuarios, trámites, tipos de cliente, salas, subtrámites y usuarios×trámites | Hora, Día, Mes o Año; día y rango de horas | — |
| **Monitoreo de turnos** | 27 columnas seleccionables: sucursal, estado, id, letra, número, fecha de ingreso, fecha de atención, trámite, subtrámite, derivado, usuario, email, puesto, perfil, datos del cliente (email, nombre, razón social, DNI, cédula, CUIT, n.º cliente, teléfono, tipo, datos extra), tiempo total de espera y de atención, mensajes | Sucursal, letra, número, trámite, perfil y tipo de cliente | — |
| **Auditoría** | ID, hora, usuario, sucursal, compañía, categoría, acción (más de 60 tipos: crear, actualizar o borrar cada entidad, login, logout automático, cambio de contraseña…), status y más info | Fechas; tipo (categoría, acción, usuario, status, sucursal) | Exportar |
| **Mensajes del sistema** (dashboard) | Eventos como reinicio automático de filas y desconexión de impresoras | Fechas | Exportar |

**Datos históricos de referencia** (reporte anual con rango 2024–2026; 2025 y 2026 dan prácticamente 0, así que corresponden a **2024**):

| Indicador | Valor |
|---|---|
| Ingresos | 249.205 |
| Atenciones | 214.203 |
| Abandonos | 12.609 |
| Nivel de servicio promedio | 36,9 % |
| Espera promedio | 61 min |
| Atención promedio | 3 min |
| Permanencia promedio | 63 min |

| Sala | Ingresos | Atenciones | Abandonos | Espera prom. | Atención prom. | Nivel de servicio |
|---|---|---|---|---|---|---|
| Farmacia | 159.538 | 133.679 | 10.435 | **91,5 min** | 2,2 min | **11,8 %** |
| Admisión | 70.514 | 68.518 | 1.982 | 8,7 min | 5,3 min | 81,5 % |
| Hospitalización | 12.198 | 11.991 | 192 | 10,3 min | 3,8 min | 74,8 % |
| Toma de Muestras | 6.531 | **15** | 0 | 153 min | 220 min | 21,4 % |
| CAE | 424 | 0 | 0 | — | — | — |

Toma de Muestras emitió tickets pero casi no registró atenciones en el sistema. Probablemente los pacientes se llamaban por fuera del sistema.

---

## 10. Configuraciones generales relevantes

| Parámetro | Valor |
|---|---|
| Numeración | Por trámite; letra + número |
| **Reinicio diario de numeración** | Tarea "Reinicio de filas" (`qResetQueuesTask`), **todos los trámites**, cada 1440 min a las **01:01–01:02**; próxima ejecución 22-10-2026 01:01. Se ejecuta correctamente cada día (ver "Mensajes del sistema"). |
| Alertas por trámite | Formato `amarillo;rojo` (inferido). Estándar: espera 5;10 min, atención 10;20 min, total 20;40 min, clientes en espera 5;10 |
| Alertas por grupo | 15;30 / 15;30 / 15;30 / 30;60 |
| Tipo de alerta del perfil | Por trámite (alternativa: Totalizado) |
| Tiempo máximo admisible de estadísticas | 86.400 min (60 días). Movimientos más largos no computan |
| Inactividad del puesto → Ausente | 29–30 min (10 min en dos perfiles) |
| Llamado por voz | **Desactivado** |
| Notificaciones por mail | Desactivadas (puerto 587, servidor no configurado; contraseña oculta) |
| **Citas por servidor externo** | **Activado.** Conector `http://10.6.74.157:3000/api/post/rut`, timeout de 10 s. Consulta las citas o datos por RUT al ingresarlo en el tótem |
| **Segmentación de clientes por CRM externo** | **Activado** (define "Cliente" o "No cliente" desde el tótem) |
| Servicio externo al encolar o al finalizar turno | Desactivados (sin URL) |
| Validar cliente antes de finalizar | No |
| Crear o editar clientes en el puesto | No |
| Tipificar turno al finalizar | No |
| Campos adicionales | No |
| Atención por videollamada | No |
| Tickets masivos | Deshabilitado (0) |
| Publicidad en ticket | No |
| Seguridad de pantallas activas | No |
| Niveles de Pad automáticos | Sí |
| Auditoría | Activada |
| Acceso a debSign | Sí |
| **Encuestas de satisfacción** | **No existen** en el menú ni en la configuración |

**Integraciones detectadas:**

1. Conector de citas y RUT (servidor interno 10.6.74.157:3000)
2. CRM externo para el tipo de cliente
3. API `/api/terminal/queueUp` (emisión desde tótem)
4. Turnero por URL con token (pantallas web)

---

## 11. Versión e información técnica

- **debQ 3.50.1** (Sistema de trámites)
- **debSign 3.40.0** (Cartelería digital)
- **debPlayer 3.12.0** (Reproductor)
- **Empresa:** Debmedia (debmedia.com). Soporte: soporte@debmedia.com
- **Licencia:** "contactarse antes del día 2050-08-24 para mantenimiento de la licencia"
- **Frontend:** AngularJS con plantillas "debfront" (debtable, debinput), Bootstrap 3.2 y Font Awesome. El backend parece Play Framework (Java/Scala), por las páginas "Action not found" y la estructura `/assets/...`.
- **API REST interna** (JSON, misma sesión), útil para migrar datos: `/api/queues`, `/api/workers`, `/api/workerprofiles`, `/api/workerprofile/{id}`, `/api/queueGroups`, `/api/waitingrooms`, `/api/numeration/list`, `/api/numerationModes/getByQueue/{id}`, `/api/terminals`, `/api/screens`, `/api/templates/company`, `/api/configs`, `/api/tasks`, `/api/customers` (POST de búsqueda), `/api/stats` y `/api/stats/report` (POST), y en debSign `/debsign/v2/api/spublicity`, `/slide/publicity/{id}`, `/interactivePublicity/json/{id}`, `/template/{id}`, `/folder`, `/channel`.
- Hay residuos de una instalación de 2017: ids y kioscos deshabilitados en 2017–2018. Existe una sucursal 1 "informatica" que contiene las plantillas de ticket.
- **Medios:** fondos y botones de tótem de diseño propio (TURNERO V1–V4, RUT, TRÁMITES, botones), logo del hospital y video "Logo debmedia.mp4".

---

## 12. Observaciones (problemas, confusiones y limitaciones)

**Estado general**

1. **Sistema prácticamente fuera de uso desde el 20-01-2025.** Se deshabilitaron 19 trámites, 6 salas y 5 kioscos ese día. Desde entonces no hay ingresos registrados. Aun así siguen encendidos 10 TVs y 4 kioscos, y corre el reinicio nocturno. Conviene confirmar con UGAA y Farmacia qué usan hoy en su lugar.
2. **Configuración inconsistente tras la desactivación:**
   - CAE está activo pero su sala está deshabilitada.
   - 32 de 36 perfiles de puesto quedaron sin trámites.
   - Los kioscos 12–18 tienen asignada una plantilla de TV ("Turnero V2") en vez del flujo de tótem.
   - Los submenús del tótem (Admisión, Farmacia, Hospitalización) quedaron huérfanos.
   - Las pantallas 1–7 y 10–15 muestran solo trámites deshabilitados.

**Errores de configuración**

3. **El botón "OIRS" del tótem emite turnos del trámite CAE (letra Z)**, no del trámite "Oirs" (letra A). Además, "Oirs" usa la letra **A**, la misma que "Preferencial" y que varios trámites de prueba.
4. **Nombres en pantalla duplicados:** H-MOD 16 y H-MOD 18 se anuncian ambos como "MOD 18", y A-MOD 00 y A-MOD 08 como "MOD 8". Además, F-MOD 30 aparece como "MOD 40" y TM-Infectología tiene perfil "TM - Trasplantados". Esto confunde al paciente frente a la TV.
5. **Basura de configuración:** unos 25 trámites de prueba ("Trámite 1…40", "anticoagulantes1", Farmacia A–F) con prefijos como `[`, `\`, `]`, `^`, `` ` ``, 6 plantillas de ticket, unas 32 publicidades duplicadas ("HGF - PTotemPad(3)(3)(1)") y 21 "Box" de hospitalización sin uso aparente.

**Datos y seguridad**

6. **CRM con datos sucios:** 250.752 "clientes" con registros basura (RUT "K", "KKK", "Sin Información"). Esto revela que el tótem guarda lo que se digita sin validar el dígito verificador.
7. **Privacidad:** el ticket impreso incluye **nombre completo y RUT** del paciente, y la vista de monitoreo puede mostrar teléfono, email y RUT a cualquier usuario con acceso.
8. **Seguridad:** hay **30 usuarios con rol administrador**, todos con permiso para modificar perfiles. Varios puestos y usuarios tienen nombre de persona en lugar de nombre funcional.

**Desempeño histórico (2024)**

9. **Farmacia** promediaba **91 min de espera** con un nivel de servicio de **11,8 %** y concentró el 64 % de los ingresos y el 83 % de los abandonos (10.435). Es el principal dolor que el sistema nuevo debe resolver: más puestos, citación por bloque horario, aviso por SMS o WhatsApp, etc.
10. **Toma de Muestras** emitía tickets (6.531) pero registró solo 15 atenciones, es decir, el personal no usaba la consola.

**Limitaciones funcionales** (requisitos a cubrir en el sistema nuevo)

11. El funcionamiento actual tiene estas carencias:
    - sin **llamado por voz** (desactivado)
    - sin opción de idioma ni accesibilidad en el tótem
    - sin **encuestas de satisfacción**
    - sin notificaciones al paciente (SMS, WhatsApp o mail)
    - sin horarios por trámite (solo por botón, y todos en 24/7)
    - atención preferente solo como "trámite Preferencial" elegido por el propio paciente, sin regla automática por edad o condición
12. **Usabilidad del panel:**
    - las fechas solo se cambian con *datepicker* (no se puede escribir) y las tablas paginan de a 5–10 filas
    - la sesión se cierra sola (aparece "Deslogueo Automático" en auditoría)
    - abrir un puesto desde "Puestos de atención" lo conecta, lo que hace riesgoso explorar
    - la sincronización es por *polling* asíncrono cada 3 s en lugar de WebSocket
    - algunos endpoints de sucursal devuelven *Unauthorized* para el administrador de sucursal, por lo que la numeración preferente o de movilidad reducida no se puede ver
13. **Hardware:** 5 de 9 kioscos están offline y hay 1 impresora con error. La hora del servidor (CLST) está bien sincronizada.
14. **Reportes:** el reporte anual agrupa mal los rangos. Con 2024–2026 muestra datos, pero 2025 y 2026 por separado dan 0, así que en la práctica todo es 2024. Tampoco hay desglose numérico por trámite en tabla, solo gráfico; para eso hay que ir a Estadísticas.

---

### Anexo A: Recomendaciones para la especificación del sistema nuevo

- Migrar el **catálogo vigente real**: TM General (T), TM Infectología (J), TM Diabetes (K), CAE (Z) y OIRS. Validar con las jefaturas si Admisión, Farmacia y Hospitalización volverán a usar filas.
- Replicar lo que sí funcionaba:
  - letra por trámite con reinicio diario
  - prioridad numérica más envejecimiento
  - perfiles de puesto con botones configurables
  - derivación entre trámites
  - estado "No se presentó"
  - pausa por inactividad
  - TV con últimos 4 llamados y parpadeo
  - integración con la agenda por RUT
- Agregar:
  - llamado por voz
  - validación de RUT (módulo 11)
  - ticket sin datos personales (o con iniciales)
  - prioridad preferente automática (por edad desde la agenda)
  - aviso por WhatsApp o SMS
  - encuesta de satisfacción
  - dashboards por hora
  - roles mínimos (pocos administradores)
- Exportar el histórico necesario antes de dar de baja: Estadísticas y Movimientos en Excel. No hace falta migrar la base CRM, porque se puede obtener de la fuente oficial (agenda o ficha).
