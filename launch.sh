#!/bin/bash
# Launch Braze SDK Demo Builder (Chainlit Chat UI)

set -e

PORT="${1:-7800}"

echo "==================================="
echo "Braze SDK Demo Builder"
echo "Chainlit Chat UI"
echo "==================================="

# Change to script directory
cd "$(dirname "$0")/code"

export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Find a Python with the required packages installed.
# Honors PYTHON env var if set, otherwise checks python3 then versioned variants.
find_python() {
    if [ -n "$PYTHON" ]; then
        if "$PYTHON" -c "import chainlit, langchain_openai" 2>/dev/null; then
            echo "$PYTHON"
            return
        fi
        echo "Error: PYTHON=$PYTHON does not have chainlit installed." >&2
        echo "Run: $PYTHON -m pip install -r requirements.txt" >&2
        exit 1
    fi

    for cmd in python3 python3.13 python3.12 python3.11 python3.10; do
        if command -v "$cmd" >/dev/null 2>&1 && "$cmd" -c "import chainlit, langchain_openai" 2>/dev/null; then
            echo "$cmd"
            return
        fi
    done

    echo "Error: No Python found with chainlit installed." >&2
    echo "Run: pip install -r requirements.txt" >&2
    exit 1
}

PYTHON_CMD=$(find_python)
echo "Using: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
echo "Launching on http://localhost:${PORT}"
echo ""

$PYTHON_CMD -m chainlit run braze_code_gen/chainlit_app.py --port "$PORT"
