#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Accept CLAUDE_PROXY_API_DOCKER_REGISTRY_URI from the user or use the environment variable. If both are empty, warn and exit.
CLAUDE_PROXY_API_DOCKER_REGISTRY_URI=${1:-${CLAUDE_PROXY_API_DOCKER_REGISTRY_URI:-""}}
if [ -z "$CLAUDE_PROXY_API_DOCKER_REGISTRY_URI" ]; then
  echo "Error: CLAUDE_PROXY_API_DOCKER_REGISTRY_URI is not set. Please provide it as an argument or set the environment variable."
  exit 1
fi

export DOCKER_CLI_EXPERIMENTAL=enabled

# Define platforms to build for
PLATFORMS=("arm64" "amd64")

# Enable emulation if it's not already enabled
echo "Enabling emulation..."
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Install qemu-user-static if not already installed
if ! dpkg -l | grep -qw qemu-user-static; then
  echo "Installing qemu-user-static..."
  sudo apt-get update
  sudo apt-get install -y qemu-user-static
fi

for PLATFORM in "${PLATFORMS[@]}"; do
  # Check if the buildx is available for the specified platform
  BUILDER_NAME="${PLATFORM}builder"
  if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
	echo "Creating a new builder instance named $BUILDER_NAME..."
	# Create a new builder instance
	docker buildx create --name "$BUILDER_NAME"
  fi

  # Switch to the new builder instance
  echo "Switching to $BUILDER_NAME..."
  docker buildx use "$BUILDER_NAME"

  # Build the image for the specified platform
  echo "Building the image for $PLATFORM..."
  docker buildx build --platform linux/"$PLATFORM" --no-cache . -t claude-proxy-api:${PLATFORM}-latest --load

  # Tag the image with the registry URI and platform
  echo "Tagging Docker image with platform..."
  docker tag claude-proxy-api:${PLATFORM}-latest ${CLAUDE_PROXY_API_DOCKER_REGISTRY_URI}/claude-proxy-api:${PLATFORM}-latest

  # Push the image to the registry
  echo "Pushing Docker image to registry..."
  docker push ${CLAUDE_PROXY_API_DOCKER_REGISTRY_URI}/claude-proxy-api:${PLATFORM}-latest
done

echo "Build and push for all platforms completed."
