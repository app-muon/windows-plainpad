@echo off
pyinstaller --onefile --windowed --name plainpad plainpad.py
echo.
echo Build complete. Output is in the dist\ folder.
pause
