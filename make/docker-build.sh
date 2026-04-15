#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_USER="${DOCKER_USER:-carlosrabelo}"
VERSION="${VERSION:-latest}"

# Use legacy builder — BuildKit has DNS resolution issues in some Docker setups
export DOCKER_BUILDKIT=0

echo "Building Docker images for $DOCKER_USER:$VERSION..."

docker build \
    -t "$DOCKER_USER/ogaden-engine:$VERSION" \
    -t "$DOCKER_USER/ogaden-engine:latest" \
    -f "$ROOT_DIR/docker/engine/Dockerfile" "$ROOT_DIR"

docker build \
    -t "$DOCKER_USER/ogaden-dashboard:$VERSION" \
    -t "$DOCKER_USER/ogaden-dashboard:latest" \
    -f "$ROOT_DIR/docker/dashboard/Dockerfile" "$ROOT_DIR"

echo "Done building."
