@echo off
rem Opens the tune-by-ear window. Nothing plays until every readiness box is ticked and Start is pressed.
rem Before starting: earbuds' own noise cancelling off, Windows volume at about 10-20 percent.
rem For the earlier engine, run: tune.bat --engine v2
cd /d "%~dp0"
".venv\Scripts\python.exe" -m anc_lab tune %*
pause
