#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Starting farmOS at http://localhost:8888"
export CONTAINERS_CONF="$DIR/containers.conf"
# Also need to set home for storage config if not fully respecting conf file
export HOME="$DIR"
podman-compose up -d
echo "Logs:"
podman-compose logs -f
