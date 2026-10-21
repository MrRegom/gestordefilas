"""Agente de impresión del tótem.

Servidor HTTP local (solo 127.0.0.1) que recibe tickets desde la pantalla del
tótem y los imprime en la impresora térmica vía el spooler de Windows (RAW).

    python agente.py                       # imprime en "POS80 Printer"
    python agente.py --impresora "Otra"
    python agente.py --simular             # no imprime; guarda los bytes en ./simulados (para pruebas)

Endpoints:
    GET  /estado    -> {"estado": "lista" | "sin papel" | ...}
    POST /imprimir  -> JSON del ticket (ver escpos.ticket)
"""
import argparse
import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import escpos

PUERTO = 8765
log = logging.getLogger("agente")

# Bits de PRINTER_INFO_2.Status (winspool.h).
ESTADOS_WINDOWS = {
    0x00000002: "con error",
    0x00000008: "atasco de papel",
    0x00000010: "sin papel",
    0x00000080: "fuera de línea",
    0x00000400: "imprimiendo",
    0x00040000: "sin tóner/tinta",
    0x00400000: "tapa abierta",
}


class Impresora:
    def __init__(self, nombre, simular):
        self.nombre = nombre
        self.simular = simular
        self.candado = threading.Lock()  # un ticket a la vez
        if simular:
            self.carpeta = Path("simulados")
            self.carpeta.mkdir(exist_ok=True)
        else:
            import win32print
            self.win32print = win32print

    def estado(self):
        if self.simular:
            return "lista (simulada)"
        try:
            h = self.win32print.OpenPrinter(self.nombre)
        except Exception:
            return "no instalada"
        try:
            info = self.win32print.GetPrinter(h, 2)
        finally:
            self.win32print.ClosePrinter(h)
        if info["Attributes"] & 0x00000400:  # PRINTER_ATTRIBUTE_WORK_OFFLINE
            return "fuera de línea"
        problemas = [texto for bit, texto in ESTADOS_WINDOWS.items() if info["Status"] & bit]
        return ", ".join(problemas) or "lista"

    def imprimir(self, datos):
        with self.candado:
            if self.simular:
                archivo = self.carpeta / f"{datetime.now():%Y%m%d-%H%M%S-%f}.bin"
                archivo.write_bytes(datos)
                return
            h = self.win32print.OpenPrinter(self.nombre)
            try:
                self.win32print.StartDocPrinter(h, 1, ("Ticket gestorfilas", None, "RAW"))
                self.win32print.StartPagePrinter(h)
                self.win32print.WritePrinter(h, datos)
                self.win32print.EndPagePrinter(h)
                self.win32print.EndDocPrinter(h)
            finally:
                self.win32print.ClosePrinter(h)


def crear_manejador(impresora):
    class Manejador(BaseHTTPRequestHandler):
        def _responder(self, codigo, cuerpo=None):
            datos = json.dumps(cuerpo or {}).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            # Chrome exige esto para que una página de la red llame a 127.0.0.1.
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
            self.wfile.write(datos)

        def do_OPTIONS(self):
            self._responder(204)

        def do_GET(self):
            if self.path == "/estado":
                self._responder(200, {"estado": impresora.estado(), "impresora": impresora.nombre})
            else:
                self._responder(404, {"error": "no existe"})

        def do_POST(self):
            if self.path != "/imprimir":
                return self._responder(404, {"error": "no existe"})
            try:
                largo = int(self.headers.get("Content-Length", 0))
                ticket = json.loads(self.rfile.read(largo))
                impresora.imprimir(escpos.ticket(ticket))
            except (ValueError, KeyError) as e:
                log.warning("Ticket inválido: %s", e)
                return self._responder(400, {"error": f"ticket inválido: {e}"})
            except Exception as e:
                log.exception("Error al imprimir")
                return self._responder(500, {"error": f"no se pudo imprimir: {e}"})
            log.info("Impreso %s", ticket.get("codigo"))
            self._responder(200, {"ok": True})

        def log_message(self, formato, *args):
            log.debug(formato, *args)

    return Manejador


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--impresora", default="POS80 Printer")
    p.add_argument("--puerto", type=int, default=PUERTO)
    p.add_argument("--simular", action="store_true")
    a = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("agente.log", encoding="utf-8")],
    )
    impresora = Impresora(a.impresora, a.simular)
    servidor = ThreadingHTTPServer(("127.0.0.1", a.puerto), crear_manejador(impresora))
    log.info("Agente escuchando en http://127.0.0.1:%s (impresora: %s, estado: %s)",
             a.puerto, a.impresora, impresora.estado())
    servidor.serve_forever()


if __name__ == "__main__":
    main()
