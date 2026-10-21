"""Prueba de impresion de ticket en impresora termica POS80 (ESC/POS) desde Windows.

Envia bytes ESC/POS en modo RAW a traves del spooler de Windows, usando el
driver ya instalado ("POS80 Printer"). No requiere conocer el puerto USB.

Uso:
    python imprimir_ticket.py --listar
    python imprimir_ticket.py
    python imprimir_ticket.py --impresora "POS80 Printer" --numero A-015 --servicio "Admision"
"""
import argparse
from datetime import datetime

import win32print

ESC, GS = b"\x1b", b"\x1d"

INICIAR = ESC + b"@"
TABLA_PC850 = ESC + b"t\x02"
CENTRO = ESC + b"a\x01"
IZQUIERDA = ESC + b"a\x00"
NEGRITA_ON, NEGRITA_OFF = ESC + b"E\x01", ESC + b"E\x00"
TAMANO_NORMAL = GS + b"!\x00"
TAMANO_ALTO = GS + b"!\x01"  # doble alto, ancho normal (cabe en 80 mm)
TAMANO_GRANDE = GS + b"!\x33"
CORTE_PARCIAL = GS + b"V\x42\x00"


def texto(s):
    return s.encode("cp850", errors="replace")


def qr(datos, modulo=6):
    d = datos.encode("ascii")
    largo = len(d) + 3
    return (
        GS + b"(k\x04\x001A2\x00"                      # modelo 2
        + GS + b"(k\x03\x001C" + bytes([modulo])       # tamano del modulo
        + GS + b"(k\x03\x001E1"                        # correccion de errores M
        + GS + b"(k" + bytes([largo % 256, largo // 256]) + b"1P0" + d
        + GS + b"(k\x03\x001Q0"                        # imprimir
    )


def armar_ticket(numero, servicio, url_qr):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M")
    return b"".join([
        INICIAR, TABLA_PC850, CENTRO,
        NEGRITA_ON, TAMANO_ALTO, texto("Hospital Dr. Gustavo Fricke\n"), NEGRITA_OFF,
        TAMANO_NORMAL, texto("Viña del Mar\n\n"),
        texto(f"{servicio}\n"),
        TAMANO_GRANDE, NEGRITA_ON, texto(f"{numero}\n"), NEGRITA_OFF, TAMANO_NORMAL,
        texto(f"\n{ahora}\n\n"),
        qr(url_qr), texto("\n"),
        texto("Espere su llamado en pantalla\n"),
        texto("Prueba: áéíóú ñ Ñ ¿?\n"),
        b"\n\n\n\n", CORTE_PARCIAL,
    ])


def imprimir(impresora, datos):
    h = win32print.OpenPrinter(impresora)
    try:
        win32print.StartDocPrinter(h, 1, ("Ticket gestorfilas", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, datos)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--listar", action="store_true", help="lista las impresoras instaladas")
    p.add_argument("--impresora", default="POS80 Printer")
    p.add_argument("--numero", default="A-001")
    p.add_argument("--servicio", default="Admisión")
    p.add_argument("--qr", default="https://hospital.example/ticket/A-001")
    a = p.parse_args()

    if a.listar:
        for _, _, nombre, _ in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
            print(nombre)
        return

    imprimir(a.impresora, armar_ticket(a.numero, a.servicio, a.qr))
    print(f"Ticket {a.numero} enviado a '{a.impresora}'.")


if __name__ == "__main__":
    main()
