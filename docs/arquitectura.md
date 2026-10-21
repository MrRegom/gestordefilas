# gestorfilas — Arquitectura y plan por etapas

Gestor de filas para el Hospital Dr. Gustavo Fricke (Unidad TIC / Integraciones).
Reemplaza a Debmedia (ver `auditoria_debmedia_hgf.md`).

## 1. Objetivos

- **No caerse:** sin punto único de falla; tótems y pantallas siguen funcionando ante cortes breves.
- **Tiempo real:** un llamado aparece en la TV en menos de 1 s (WebSockets, no polling).
- **Liviano:** pantallas y tótems corren en NUC antiguos (Chromium en modo kiosko).
- **Escalable a muchas unidades:** se diseña multi-unidad desde el día 1, aunque se parta con ~20.
- **Trazabilidad completa:** cada cambio de estado de cada ticket queda registrado con hora, funcionario y puesto.

## 2. Modelo multi-unidad

Toda la configuración cuelga de una jerarquía; agregar una unidad es configuración, no código.

```
Establecimiento (Hospital Fricke; a futuro otros del Servicio de Salud)
└── Unidad (Toma de Muestras, Farmacia, Admisión, CAE, OIRS…)
    ├── Sala de espera
    ├── Servicio / fila (letra, numeración, prioridad, horario, alertas)
    ├── Puesto (nombre único en pantalla, perfil)
    ├── Tótem (servicios que ofrece, impresora)
    └── Pantalla TV (servicios / salas que muestra)
```

- Permisos por unidad: un supervisor ve y administra solo su unidad.
- Numeración y reinicio diario por servicio.
- Los canales de tiempo real se separan por unidad/sala, así una unidad no afecta a otra.

## 3. Componentes

| Componente | Tecnología | Rol |
|---|---|---|
| Backend | Django + Django REST Framework | Lógica, API, administración, reportes |
| Tiempo real | Django Channels + Redis | Empuja eventos a TV, puestos, tótems y supervisión |
| Base de datos | PostgreSQL (primaria + réplica) | Configuración, tickets, eventos |
| Tareas | Celery (o worker de Channels) | Reinicio diario, alertas, reportes, notificaciones |
| Proxy | Nginx | TLS, balanceo entre instancias, estáticos |
| Pantalla TV | HTML + CSS + JS puro | Últimos llamados, voz (speechSynthesis), reconexión automática |
| Tótem | HTML + JS liviano + **agente local** Python | UI táctil; el agente imprime ESC/POS y reporta estado de impresora |
| Puesto funcionario | Web (HTMX o React liviano) | Llamar, re-llamar, atender, derivar, finalizar, no se presentó, pausa |
| Despliegue | Docker Compose (luego opcional Kubernetes) | Mismo artefacto en pruebas y producción, rollback simple |

## 4. Trazabilidad

- `Ticket`: estado actual (emitido, llamado, en atención, derivado, finalizado, no se presentó, cancelado).
- `EventoTicket` (solo inserción, nunca se edita): tipo, timestamp, funcionario, puesto, servicio origen/destino, datos extra.
- Métricas derivadas de los eventos: espera, atención, permanencia, abandono, nivel de servicio, productividad por funcionario/puesto, horas peak.
- Auditoría separada de acciones administrativas (quién cambió qué configuración).

## 5. Robustez

1. Dos o más instancias de aplicación tras Nginx; Redis y PostgreSQL con respaldo.
2. Clientes (TV, puesto, tótem) reconectan solos y reciben el estado completo al volver.
3. Tótem en modo degradado: si el servidor no responde, imprime con numeración de contingencia y sincroniza después.
4. Panel de salud para TIC: dispositivos en línea, impresoras sin papel/error, latencias; alertas.
5. Pruebas de carga antes de producción: 5× el volumen real (≥5.000 tickets/día, todos los dispositivos conectados).
6. Respaldos automáticos diarios y prueba de restauración.

## 6. Privacidad y seguridad

- Ticket sin nombre ni RUT (solo número, servicio, hora, QR).
- RUT validado con dígito verificador; datos personales mínimos y solo si el servicio lo requiere.
- Roles mínimos (pocos administradores), login con usuarios del hospital (LDAP/AD a evaluar).

## 7. Plan por etapas

| Etapa | Entregable |
|---|---|
| 0 ✅ | Prueba de impresión ESC/POS en tótem POS80 (`herramientas/prueba_impresora`) |
| 1 ✅ | Núcleo: modelo multi-unidad, servicios, tickets, eventos, numeración, admin |
| 2 ✅ | Tótem + agente de impresión |
| 3 | Puesto del funcionario |
| 4 | Pantalla TV en tiempo real con voz |
| 5 | Piloto en una unidad (p. ej. Toma de Muestras) |
| 6 | Supervisión en vivo, reportes y exportación a Excel |
| 7 | Panel de salud de dispositivos, pruebas de carga, alta disponibilidad |
| 8 | Integraciones (citas por RUT, prioridad automática Ley 21.168, WhatsApp/SMS, encuestas) y expansión a más unidades |
