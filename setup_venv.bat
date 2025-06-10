@echo off
echo Checking for Python launcher (py.exe)...

where py >nul 2>&1
if %errorlevel% neq 0 (
    echo Python launcher (py.exe) not found in PATH.
    echo Please ensure Python is installed correctly from python.org and the launcher is available.
    echo Alternatively, you can try changing 'py' back to 'python' in this script if 'python' works for you and the issue was different.
    pause
    exit /b 1
)

echo Found Python launcher.
echo Creating virtual environment in .\.venv\ using 'py -m venv .venv' ...
py -m venv .venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment using 'py -m venv .venv'.
    echo Make sure 'venv' module is available for your Python installation (usually included).
    pause
    exit /b 1
)

echo Virtual environment created.
echo Installing dependencies from requirements.txt...
call .\.venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install requirements. Check requirements.txt and your internet connection.
    pause
    exit /b 1
)

echo Dependencies installed successfully.
echo.
echo --- Setup Complete ---
echo To activate the virtual environment, run the following command in this terminal:
echo   .\.venv\Scripts\activate
echo.
echo After activation, you can run the bot using:
echo   py name_changer_bot.py
echo (Or, to be very specific after activating: .\.venv\Scripts\python.exe name_changer_bot.py)
echo.
pause
exit /b 0