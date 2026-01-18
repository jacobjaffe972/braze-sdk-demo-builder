#!/bin/bash
# Launch Braze SDK Landing Page Generator (Streamlit UI)

set -e

echo "==================================="
echo "Braze Landing Page Generator"
echo "Streamlit UI"
echo "==================================="

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -d "code/.venv" ]; then
    echo "Activating code/.venv..."
    source code/.venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating venv..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating .venv..."
    source .venv/bin/activate
else
    echo "No virtual environment found. Using system Python."
fi

# Install braze_code_gen package in development mode
echo "Installing braze_code_gen package..."
cd code
python3 -m pip install -e . > /dev/null 2>&1
cd ..

# Check dependencies
echo "Checking dependencies..."
python3 -c "import streamlit" 2>/dev/null || {
    echo "Streamlit not installed. Installing..."
    python3 -m pip install "streamlit>=1.30.0"
}

# Launch Streamlit
echo "Launching Streamlit UI..."
echo "Access at: http://localhost:7860"
echo ""

streamlit run code/braze_code_gen/ui/streamlit_app.py \
    --server.port 7860 \
    --browser.gatherUsageStats false \
    --server.enableXsrfProtection false \
    --server.enableCORS false \
    --server.address localhost
