@echo off
rem Inicia el agente de impresion. Copiar un acceso directo a este archivo en
rem shell:startup para que arranque con Windows.
cd /d "%~dp0"
:bucle
pythonw agente.py
rem Si el agente se cae, se reinicia a los 5 segundos.
timeout /t 5 /nobreak >nul
goto bucle
