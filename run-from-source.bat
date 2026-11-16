@echo off
rem Fallback when the .exe does not start: needs Python 3.12 from python.org ("py" launcher). Uses Microsoft Edge.
cd /d "%~dp0"
py -3 -m pip install --quiet -r requirements.txt
py -3 saver.py %*
pause
