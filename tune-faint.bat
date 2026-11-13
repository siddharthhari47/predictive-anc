@echo off
rem Opens the tune-by-ear window with the faint-hum detector added (weak, slightly wobbly hums such as a fan).
rem It takes about 9 seconds of steady hum before a tone shows up. Nothing plays until every readiness box is ticked and Start is pressed.
rem Before starting: earbuds' own noise cancelling off, Windows volume at about 10-20 percent.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m anc_lab tune --engine faint %*
pause
