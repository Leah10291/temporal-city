@echo off
cd /d "%~dp0"
echo Installing requirements...
py -m pip install -q -r requirements.txt
py app.py
pause
