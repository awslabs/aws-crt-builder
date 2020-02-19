#!/usr/bin/env bash

set -ex

if [ $# -lt 6 ]; then
  echo Usage: $0 REGISTRY USERNAME PASSWORD IMAGE_NAME IMAGE_TAG CONTEXT (EXTRA_ARGS)
fi

INPUT_REGISTRY=$1
shift
INPUT_USERNAME=$1
shift
INPUT_PASSWORD=$1
shift
INPUT_IMAGE_NAME=$1
shift
INPUT_IMAGE_TAG=$1
shift
INPUT_CONTEXT=$1
shift
# gather up whatever is left
INPUT_BUILD_EXTRA_ARGS=$1 $2 $3 $4 $5 $6 $7 $8 $9

BUILDX_VERSION=v0.3.1

_get_full_image_name() {
  echo ${INPUT_REGISTRY:+$INPUT_REGISTRY/}${INPUT_IMAGE_NAME}
}

install_buildx() {
  buildx_tag=$BUILDX_VERSION
  docker_plugins_path=$HOME/.docker/cli-plugins
  buildx_release_url=https://github.com/docker/buildx/releases/download/$buildx_tag/buildx-$buildx_tag.linux-amd64

  mkdir -p $docker_plugins_path
  curl -L -0 $buildx_release_url -o $docker_plugins_path/docker-buildx
  chmod a+x $docker_plugins_path/docker-buildx
  docker buildx version
}

configure_buildx() {
  docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
  docker buildx create --name builder --driver docker-container --use
  docker buildx inspect --bootstrap
  docker buildx install
}

login_to_registry() {
  echo "${INPUT_PASSWORD}" | docker login -u "${INPUT_USERNAME}" --password-stdin "${INPUT_REGISTRY}"
}

build_image() {
  # pull cache, ignore failure if it doesn't exist
  docker pull "$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG}-builder || true
  # build builder target image
  docker build \
    --file=${INPUT_CONTEXT}/${INPUT_DOCKERFILE} \
    --target=builder \
    --tag="$(_get_full_image_name)":${INPUT_IMAGE_TAG}-builder \
    --load \
    --cache-from="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    ${INPUT_BUILD_EXTRA_ARGS} \
    ${INPUT_CONTEXT}

  # pull previous image
  docker pull "$(_get_full_image_name)":${INPUT_IMAGE_TAG} || true
  # build final image
  docker build \
    --file=${INPUT_CONTEXT}/${INPUT_DOCKERFILE} \
    --target=builder \
    --tag="$(_get_full_image_name)":${INPUT_IMAGE_TAG}-builder \
    --load \
    --cache-from="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    ${INPUT_BUILD_EXTRA_ARGS} \
    ${INPUT_CONTEXT}

  # push image
  docker push "$(_get_full_image_name)":${INPUT_IMAGE_TAG}
  # push cache
  docker push "$(_get_full_image_name)":${INPUT_IMAGE_TAG}-builder
}

logout_from_registry() {
  docker logout "${INPUT_REGISTRY}"
}

login_to_registry
install_buildx
configure_buildx
build_image
logout_from_registry