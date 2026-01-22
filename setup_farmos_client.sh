#!/bin/bash
set -e

# Ensure Pyenv is available
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

echo "Creating virtualenv..."
if [ ! -d "farmos-venv" ]; then
    python -m venv farmos-venv
fi

source farmos-venv/bin/activate

echo "Installing farmOS library and MCP SDK..."
pip install farmOS mcp

echo "Verifying installation..."
python -c "import farmOS; print('farmOS library installed at:', farmOS.__file__)"
