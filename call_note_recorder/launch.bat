@echo off
title Call Note Recorder
:: Run from this file's own folder so it works no matter where the shortcut lives.
cd /d "%~dp0"
python main.py
:: Keep the window open if the app exits with an error, so the message is readable.
if errorlevel 1 (
    echo.
    echo The app exited with an error. Details are above and in the log file.
    pause
)
