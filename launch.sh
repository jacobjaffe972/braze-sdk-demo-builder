#!/bin/bash
# Launch Braze SDK Code Generator (Chainlit Chat UI)

set -e

PORT="${1:-7800}"

echo "==================================="
echo "Braze SDK Code Generator"
echo "Chainlit Chat UI"
echo "==================================="

# Change to script directory
cd "$(dirname "$0")/code"

export PYTHONPATH="${PWD}:${PYTHONPATH}"

echo "Launching on http://localhost:${PORT}"
echo ""

python3.13 -m chainlit run braze_code_gen/chainlit_app.py --port "$PORT"
