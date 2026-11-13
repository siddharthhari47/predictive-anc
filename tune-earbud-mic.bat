@echo off
rem Opens the tune-by-ear window listening through the earbuds' own microphone instead of the laptop's.
rem Uses the faint-hum detector, as tune-faint.bat does. Nothing plays until every readiness box is ticked and Start is pressed.
rem Before starting: earbuds plugged in, their own noise cancelling off, Windows volume at about 10-20 percent.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m anc_lab tune --mic earbuds --engine faint %*
pause
