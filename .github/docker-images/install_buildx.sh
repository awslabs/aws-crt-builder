#!/bin/sh

set -ex

BUILDX_TAG=v0.3.1
DOCKER_PLUGINS_PATH=~/.docker/cli-plugins
BUILDX_RELEASE_URL=https://github.com/docker/buildx/releases/download/$BUILDX_TAG/buildx-$BUILDX_TAG.linux-amd64

mkdir -p $DOCKER_PLUGINS_PATH
curl -L $BUILDX_RELEASE_URL -o $DOCKER_PLUGINS_PATH/docker-buildx
docker buildx version
docker buildx build --help