# Agente del tótem

Corre en cada tótem (NUC con Windows 11). Recibe los tickets desde la pantalla
del tótem (Chrome en modo kiosko) y los imprime en la impresora térmica POS80.

```
Pantalla tótem (Chrome)  --1. emitir-->  Servidor gestorfilas
        |
        +--2. imprimir--> Agente local (127.0.0.1:8765) --> POS80 (USB)
```

Si la impresora falla, el número igual queda emitido y la pantalla lo muestra
para que el paciente lo anote; el estado de la impresora se informa al servidor
cada minuto y queda visible en el admin (ficha del tótem).

## Instalación en el tótem

1. Python 3.11+ (marcar "Add to PATH") y `pip install pywin32`.
2. Copiar esta carpeta a `C:\gestorfilas\agente_totem`.
3. Probar: `python agente.py` y en el navegador abrir http://127.0.0.1:8765/estado
4. Arranque automático: `Win + R` → `shell:startup` → pegar accesos directos a
   `iniciar_agente.bat` y a `iniciar_totem.bat` (editar en este último SERVIDOR y TOKEN).

## Probar sin impresora

`python agente.py --simular` guarda cada ticket en `simulados/` en vez de imprimir.
