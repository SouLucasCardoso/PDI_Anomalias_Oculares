@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0desconectar_app_usb.ps1"
pause
