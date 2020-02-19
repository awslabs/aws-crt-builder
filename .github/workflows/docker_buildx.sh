#!/usr/bin/env bash

set -ex

if [ $# -lt 6 ]; then
  echo "Usage: $0 REGISTRY USERNAME PASSWORD IMAGE_NAME IMAGE_TAG CONTEXT (EXTRA_ARGS)"
fi

trim() {
  local var="$*"
  # remove leading whitespace characters
  var="${var#"${var%%[![:space:]]*}"}"
  # remove trailing whitespace characters
  var="${var%"${var##*[![:space:]]}"}"   
  echo -n "$var"
}

INPUT_REGISTRY=$(trim $1)
shift
INPUT_USERNAME=$(trim $1)
shift
INPUT_PASSWORD=$(trim $1)
shift
INPUT_IMAGE_NAME=$(trim $1)
shift
INPUT_IMAGE_TAG=$(trim $1)
shift
INPUT_CONTEXT=$(trim $1)
shift
# gather up whatever is left
INPUT_BUILD_EXTRA_ARGS="$(trim $1) $(trim $2) $(trim $3) $(trim $4) $(trim $5) $(trim $6) $(trim $7) $(trim $8) $(trim $9)"

BUILDX_VERSION=v0.3.1

_get_full_image_name() {
  echo ${INPUT_REGISTRY:+$INPUT_REGISTRY/}${INPUT_IMAGE_NAME}
}

install_buildx() {
  $(dirname $0)/install_buildx.sh
}

login_to_registry() {
  echo "${INPUT_PASSWORD}" | docker login -u "${INPUT_USERNAME}" --password-stdin "${INPUT_REGISTRY}"
}

build_image() {
  # pull cache, ignore failure if it doesn't exist
  docker pull "$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} || true
  # build builder target image
  docker build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --tag="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    --load \
    --cache-from="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    ${INPUT_BUILD_EXTRA_ARGS} \
    ${INPUT_CONTEXT}

  # pull previous image, ignore failure if it doesn't exist
  docker pull "$(_get_full_image_name)":${INPUT_IMAGE_TAG} || true
  # build final image
  docker build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --tag="$(_get_full_image_name)":${INPUT_IMAGE_TAG} \
    --load \
    --cache-from="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    --cache-from="$(_get_full_image_name)":${INPUT_IMAGE_TAG} \
    ${INPUT_BUILD_EXTRA_ARGS} \
    ${INPUT_CONTEXT}

  # push image
  docker push "$(_get_full_image_name)":${INPUT_IMAGE_TAG}
  # push cache
  docker push "$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG}
}

logout_from_registry() {
  docker logout "${INPUT_REGISTRY}"
}

login_to_registry
install_buildx
build_image
logout_from_registry

