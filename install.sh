#!/bin/bash
set -e

# Ensure we are in the right directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Initializing Podman..."
# Create necessary data directories
mkdir -p sites
mkdir -p db-data

# Ensure sites directory is writable by the container (often needed for rootless podman)
chmod 777 sites
chmod 777 db-data

echo "Pulling images..."
export CONTAINERS_CONF="$DIR/containers.conf"
export HOME="$DIR"
podman-compose pull
