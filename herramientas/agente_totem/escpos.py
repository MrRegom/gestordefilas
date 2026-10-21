"""Construcción de tickets en bytes ESC/POS para impresoras térmicas de 80 mm (POS80)."""

ESC, GS = b"\x1b", b"\x1d"

INICIAR = ESC + b"@"
TABLA_PC850 = ESC + b"t\x02"
CENTRO = ESC + b"a\x01"
NEGRITA_ON, NEGRITA_OFF = ESC + b"E\x01", ESC + b"E\x00"
TAMANO_NORMAL = GS + b"!\x00"
TAMANO_ALTO = GS + b"!\x01"   # doble alto, ancho normal
TAMANO_GRANDE = GS + b"!\x33"  # 4x ancho y alto, para el número
CORTE_PARCIAL = GS + b"V\x42\x00"


def texto(s):
    return s.encode("cp850", errors="replace")


def qr(datos, modulo=6):
    d = datos.encode("ascii", errors="replace")
    largo = len(d) + 3
    return (
        GS + b"(k\x04\x001A2\x00"
        + GS + b"(k\x03\x001C" + bytes([modulo])
        + GS + b"(k\x03\x001E1"
        + GS + b"(k" + bytes([largo % 256, largo // 256]) + b"1P0" + d
        + GS + b"(k\x03\x001Q0"
    )


def ticket(t):
    """`t` es el JSON que devuelve /api/totem/tickets/."""
    partes = [
        INICIAR, TABLA_PC850, CENTRO,
        NEGRITA_ON, TAMANO_ALTO, texto(f"{t['establecimiento']}\n"), NEGRITA_OFF,
        TAMANO_NORMAL, texto(f"{t['unidad']}\n\n"),
        NEGRITA_ON, texto(f"{t['servicio']}\n"), NEGRITA_OFF,
        TAMANO_GRANDE, NEGRITA_ON, texto(f"{t['codigo']}\n"), NEGRITA_OFF, TAMANO_NORMAL,
    ]
    if t.get("preferente"):
        partes.append(texto("ATENCIÓN PREFERENTE\n"))
    delante = t.get("personas_delante")
    if delante is not None:
        partes.append(texto(f"\nPersonas antes que usted: {delante}\n"))
    partes.append(texto(f"{t['emitido_en']}\n\n"))
    if t.get("qr"):
        partes += [qr(t["qr"]), texto("\n")]
    partes += [
        texto("Espere su llamado en pantalla\n"),
        texto("Ticket válido solo por hoy\n"),
        b"\n\n\n\n", CORTE_PARCIAL,
    ]
    return b"".join(partes)
