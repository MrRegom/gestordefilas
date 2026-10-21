# Prueba de impresora del tótem (POS80)

Script para verificar que el tótem (NUC con Windows 11) imprime tickets en la
impresora térmica **POS80 Printer** enviando comandos ESC/POS en modo RAW.

## Pasos (en el tótem)

1. Instalar Python 3.11 o superior desde python.org (marcar "Add to PATH").
2. Abrir PowerShell en esta carpeta e instalar la dependencia:
   ```
   pip install pywin32
   ```
3. Ver el nombre exacto de la impresora:
   ```
   python imprimir_ticket.py --listar
   ```
4. Imprimir un ticket de prueba:
   ```
   python imprimir_ticket.py
   python imprimir_ticket.py --numero B-123 --servicio "Toma de muestras"
   ```

## Qué revisar en el papel

- [ ] Imprime el ticket completo y **corta** el papel.
- [ ] El número grande se lee bien y cabe en el ancho (80 mm).
- [ ] El **QR** aparece y se puede escanear con el celular.
- [ ] Los acentos y la ñ salen correctos en la línea "Prueba".
- [ ] Tiempo desde el comando hasta que sale el ticket.

Si algo falla, envía una foto del ticket y el mensaje de error.
