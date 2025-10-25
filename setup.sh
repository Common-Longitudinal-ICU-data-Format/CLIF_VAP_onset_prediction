#!/bin/bash

# Configuration: Specify Python version preference
PREFERRED_PYTHON="python3.12"

# Try preferred version first, fallback to python3
if command -v $PREFERRED_PYTHON &> /dev/null; then
    PYTHON_CMD=$PREFERRED_PYTHON
else
    PYTHON_CMD="python3"
    echo "Warning: $PREFERRED_PYTHON not found, using $PYTHON_CMD"
fi

echo "Using: $($PYTHON_CMD --version)"

# Rest of the script remains the same
$PYTHON_CMD -m venv .vap-onset
source .vap-onset/bin/activate
python --version
pip install --upgrade pip
pip install -r requirements.txt
pip install jupyter ipykernel
python -m ipykernel install --user --name=vap-onset --display-name="Python (VAP-ONSET)"

echo "Setup complete! Virtual environment is ready."