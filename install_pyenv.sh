#!/bin/bash
set -e

# Install build dependencies for Python (commonly needed)
# sudo apt-get update && sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
# libbz2-dev libreadline-dev libsqlite3-dev llvm libncurses5-dev libncursesw5-dev \
# xz-utils tk-dev libffi-dev liblzma-dev python-openssl git
# Since we can't use sudo, we rely on pre-installed libs or hope for the best.

echo "Check for Pyenv..."
if [ -d "$HOME/.pyenv" ]; then
    echo "Pyenv directory exists, skipping installation."
else
    echo "Installing Pyenv..."
    curl https://pyenv.run | bash
fi

# Add to path for this session
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

echo "Installing Python 3.11.9..."
pyenv install 3.11.9
pyenv global 3.11.9

echo "Python version:"
python --version
