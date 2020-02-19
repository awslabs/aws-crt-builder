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
  $(dirname $0)/install_buildx.sh
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
build_image
logout_from_registry