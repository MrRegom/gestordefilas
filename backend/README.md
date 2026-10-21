# Backend gestorfilas (Django)

Núcleo del gestor de filas: modelo multi-unidad, tickets, numeración diaria y trazabilidad.

```
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver      # admin en http://localhost:8000/admin/
python manage.py test filas
```

Sin variables de entorno usa SQLite (desarrollo). Para PostgreSQL definir
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`.

- `filas/models.py`: Establecimiento → Unidad → Sala, Servicio, Puesto, Tótem, Pantalla; Ticket y EventoTicket (inmutable).
- `filas/operaciones.py`: única vía para cambiar tickets (emitir, llamar siguiente, re-llamar, atender, finalizar, no se presentó, derivar, re-encolar, cancelar). Cada operación registra su evento en la misma transacción.
