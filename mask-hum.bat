@echo off
rem Hum masker: soft noise around the hum so it stands out less. Not cancellation.
rem Nothing plays until you tick every box in the window and press Start.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m anc_lab tune --mask %*
pause
