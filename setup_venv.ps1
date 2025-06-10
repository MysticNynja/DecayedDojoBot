Write-Host "Checking for Python..."

$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonPath) {
    # If python/python3 not found, try 'py' specifically for Windows Python launcher
    $pythonPath = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonPath) {
        Write-Host "Found Python launcher (py.exe). Will use this."
    } else {
        Write-Host "Python (python, python3, or py) not found in PATH. Please install Python 3 (python.org) and ensure it's added to your PATH."
        Read-Host "Press Enter to exit"
        exit 1
    }
}

$pythonExecutable = $pythonPath.Source
Write-Host "Found Python at: $pythonExecutable"

$venvDir = ".venv"

if (Test-Path $venvDir) {
    Write-Host "Virtual environment '$venvDir' already exists. Skipping creation."
} else {
    Write-Host "Creating virtual environment in $venvDir ..."
    & $pythonExecutable -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment. Make sure 'venv' module is available and your Python installation is correct."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Virtual environment created."
}


Write-Host "Installing dependencies from requirements.txt..."

$pipPath = Join-Path -Path (Get-Location) -ChildPath (Join-Path -Path $venvDir -ChildPath "Scripts\pip.exe")

if (-not (Test-Path $pipPath)) {
    Write-Host "ERROR: pip.exe not found in virtual environment at $pipPath"
    Write-Host "Please ensure the virtual environment was created successfully in the '$venvDir' folder."
    Read-Host "Press Enter to exit"
    exit 1
}

& $pipPath install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install requirements. Check requirements.txt, your internet connection, or try running pip install manually after activating the venv."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Dependencies installed successfully."
Write-Host ""
Write-Host "--- Setup Complete ---"
Write-Host "To activate the virtual environment in this PowerShell session, run:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "After activation, you can run the bot using (for example):"
Write-Host "  python name_changer_bot.py" # Or py, or .\.venv\Scripts\python.exe
Write-Host ""
Read-Host "Press Enter to exit"
exit 0