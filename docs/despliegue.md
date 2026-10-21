# Despliegue en un servidor del hospital

## Requisitos del servidor
- Linux (Ubuntu 22.04/24.04 o Rocky/RHEL 9) con **Docker** y **Docker Compose**.
- 2 CPU, 4 GB RAM, 40 GB disco (sobra para el piloto).
- IP fija en la red interna, accesible desde tótems, puestos y pantallas.
- Si el servidor no tiene internet: preparar las imágenes en otro equipo (`docker save`/`docker load`).

## Primera instalación
```
git clone <repo> gestorfilas && cd gestorfilas
git checkout claude/loving-wozniak-ovkth9
cp .env.ejemplo .env          # editar claves, IP del servidor y puerto
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py cargar_demo     # opcional: datos de prueba
```
Admin: `http://IP-SERVIDOR/admin/` · Tótem: `http://IP-SERVIDOR/totem/#TOKEN`.

Generar claves seguras: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.

## Actualizar
```
git pull
docker compose up -d --build     # aplica migraciones al arrancar
```

## Operación
- Logs: `docker compose logs -f web`
- Respaldo de la base: `docker compose exec db pg_dump -U gestorfilas gestorfilas > respaldo_$(date +%F).sql`
- Los contenedores se reinician solos ante fallas o reinicio del servidor.

## Tótems
En cada tótem, en `herramientas/agente_totem/iniciar_totem.bat`, poner
`SERVIDOR=http://IP-SERVIDOR` y el token del tótem (ver README del agente).
