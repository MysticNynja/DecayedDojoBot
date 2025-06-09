@echo off
echo Checking for Python...

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH. Please install Python 3 (python.org) and ensure it's added to your PATH.
    goto :eof
)

echo Found Python.
echo Creating virtual environment in .\.venv\ ...
python -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment. Make sure 'venv' module is available.
    goto :eof
)

echo Virtual environment created.
echo Installing dependencies from requirements.txt...
call .\.venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements. Check requirements.txt and your internet connection.
    goto :eof
)

echo Dependencies installed successfully.
echo.
echo --- Setup Complete ---
echo To activate the virtual environment, run the following command in this terminal:
echo   .\.venv\Scripts\activate
echo.
echo After activation, you can run the bot using:
echo   python name_changer_bot.py
echo.
pause
:eof
