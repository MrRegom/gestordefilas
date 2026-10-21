@echo off
rem Abre la pantalla del totem en Chrome modo kiosko.
rem Reemplazar SERVIDOR y TOKEN (el token aparece en el admin, ficha del totem).
set SERVIDOR=http://SERVIDOR:8000
set TOKEN=PEGAR_TOKEN_AQUI
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk --noerrdialogs --disable-session-crashed-bubble --disable-pinch --overscroll-history-navigation=0 "%SERVIDOR%/totem/#%TOKEN%"
