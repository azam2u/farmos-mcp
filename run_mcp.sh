#!/bin/bash
cd "$(dirname "$0")"
source farmos-venv/bin/activate

# Default Environment Variables (can be overridden)
export FARMOS_HOST="${FARMOS_HOST:-https://try.farmos.net}"
export FARMOS_USER="${FARMOS_USER:-mark}"
export FARMOS_PASSWORD="${FARMOS_PASSWORD:-E1D5S9UO5O0S}"
export FARMOS_CLIENT_ID="${FARMOS_CLIENT_ID:-farm}"

# Check for Python
if ! command -v python &> /dev/null; then
    echo "Python not found in virtualenv!"
    exit 1
fi

# Run the server
python farmos_mcp.py
