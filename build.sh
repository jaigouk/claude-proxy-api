#!/bin/bash


# Exit immediately if a command exits with a non-zero status.
set -e

# Read the DOCKER_REGISTRY_URI from environment variable
DOCKER_REGISTRY_URI=${DOCKER_REGISTRY_URI:-"192.168.8.213:30501"}

# Enable Docker CLI experimental features
export DOCKER_CLI_EXPERIMENTAL=enabled

# Check if the buildx is available
if ! docker buildx ls | grep -q arm64builder; then
  echo "Creating a new builder instance named arm64builder..."
  # Create a new builder instance
  docker buildx create --name arm64builder
fi

# Switch to the new builder instance
echo "Switching to arm64builder..."
docker buildx use arm64builder

# Enable emulation if it's not already enabled
echo "Enabling emulation..."
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Install qemu-user-static if not already installed
if ! dpkg -l | grep -qw qemu-user-static; then
  echo "Installing qemu-user-static..."
  sudo apt-get update
  sudo apt-get install -y qemu-user-static
fi

# Build the image
echo "Building the image..."
docker buildx build --platform linux/arm64 --no-cache . -t claude-proxy-api:latest --load


# Tag the image with the registry URI
echo "Tagging Docker image..."
docker tag claude-proxy-api:latest ${DOCKER_REGISTRY_URI}/19hz/claude-proxy-api:latest

# Push the image to the registry
echo "Pushing Docker image to registry..."
docker push ${DOCKER_REGISTRY_URI}/19hz/claude-proxy-api:latest

echo "Build and push completed."
