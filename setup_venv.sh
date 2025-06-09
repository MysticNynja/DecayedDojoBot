#!/bin/bash
echo "Checking for Python 3..."

if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found. Please install Python 3."
    exit 1
fi

echo "Found Python 3."
PY_VERSION=$(python3 --version)
echo "Using $PY_VERSION"

VENV_DIR=".venv"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists. Skipping creation."
else
    echo "Creating virtual environment in $VENV_DIR/ ..."
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Make sure 'venv' module is available for Python 3."
        exit 1
    fi
    echo "Virtual environment created."
fi

echo "Installing dependencies from requirements.txt into $VENV_DIR ..."
# Source activate temporarily for this script's pip call, or call pip directly
if [ -f "$VENV_DIR/bin/pip" ]; then
    "$VENV_DIR/bin/pip" install -r requirements.txt
else
    echo "pip command not found in virtual environment. Trying to activate and install..."
    source "$VENV_DIR/bin/activate"
    pip install -r requirements.txt
    deactivate # Deactivate after install if sourced
fi

if [ $? -ne 0 ]; then
    echo "Failed to install requirements. Check requirements.txt and your internet connection."
    exit 1
fi

echo "Dependencies installed successfully."
echo ""
echo "--- Setup Complete ---"
echo "To activate the virtual environment, run the following command in this terminal:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "After activation, you can run the bot using:"
echo "  python3 name_changer_bot.py" # Assuming python3 for consistency
echo ""
