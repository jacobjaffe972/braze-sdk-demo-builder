#!/bin/bash
# Complete restart script - kills old processes and clears cache

echo "🔄 Restarting Braze UI with clean state..."

# 1. Kill any running UI processes
echo "1. Killing old UI processes..."
pkill -f "streamlit" 2>/dev/null || true
pkill -f "braze_code_gen" 2>/dev/null || true
sleep 1

# 2. Clear Python cache
echo "2. Clearing Python cache..."
find /Users/Jacob.Jaffe/code-gen-agent/code/braze_code_gen -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /Users/Jacob.Jaffe/code-gen-agent/code/braze_code_gen -name "*.pyc" -delete 2>/dev/null || true

# 3. Set environment
export PYTHONPATH=/Users/Jacob.Jaffe/code-gen-agent/code
export PYTHONDONTWRITEBYTECODE=1  # Prevent new .pyc files
export OPENAI_API_KEY=${OPENAI_API_KEY:-"dummy_key_for_testing"}

# 4. Launch fresh UI
echo "3. Launching fresh UI..."
cd /Users/Jacob.Jaffe/code-gen-agent/code

/Users/Jacob.Jaffe/code-gen-agent/braze-docs-mcp/venv/bin/python -m braze_code_gen "$@"
