#!/bin/bash

# Podman builder script

# 1) Pull in base image (make sure to pull in latest base images otherwise podman will prompt user)
REGISTRY="docker.io/pnispero"
REGISTRY_PATH="/mnt/eed/ad-build/registry/dockerfiles"
echo "podman pull $REGISTRY/$ADBS_OS_ENVIRONMENT-env:latest"
podman pull $REGISTRY/$ADBS_OS_ENVIRONMENT-env:latest
# 2) Build image
cd /mnt/eed/ad-build/registry/dockerfiles
echo "podman build -t $ADBS_DOCKERFILE:latest -f $REGISTRY_PATH/$ADBS_DOCKERFILE /"
podman build -t $ADBS_DOCKERFILE:latest -f $REGISTRY_PATH/$ADBS_DOCKERFILE /
# 3) Push image to registry


