#!/usr/bin/env bash
set -euo pipefail

DOCKER_USER="${DOCKER_USER:-carlosrabelo}"
VERSION="${VERSION:-latest}"

echo "Pushing Docker images for $DOCKER_USER:$VERSION..."

docker push "$DOCKER_USER/ogaden-engine:$VERSION"
docker push "$DOCKER_USER/ogaden-engine:latest"

docker push "$DOCKER_USER/ogaden-dashboard:$VERSION"
docker push "$DOCKER_USER/ogaden-dashboard:latest"

echo "Done pushing."
