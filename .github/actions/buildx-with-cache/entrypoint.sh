#!/usr/bin/env bash

set -ex

# helper functions
_exit_if_empty() {
  local var_name=${1}
  local var_value=${2}
  if [ -z "$var_value" ]; then
    echo "Missing input $var_name" >&2
    exit 1
  fi
}

# _get_max_stage_number() {
#   sed -nr 's/^([0-9]+): Pulling from.+/\1/p' "$PULL_STAGES_LOG" |
#     sort -n |
#     tail -n 1
# }

# _get_stages() {
#   grep -EB1 '^Step [0-9]+/[0-9]+ : FROM' "$BUILD_LOG" |
#     sed -rn 's/ *-*> (.+)/\1/p'
# }

_get_full_image_name() {
  echo ${INPUT_REGISTRY:+$INPUT_REGISTRY/}${INPUT_IMAGE_NAME}
}

# action steps
check_required_input() {
  _exit_if_empty USERNAME "${INPUT_USERNAME}"
  _exit_if_empty PASSWORD "${INPUT_PASSWORD}"
  _exit_if_empty IMAGE_NAME "${INPUT_IMAGE_NAME}"
  _exit_if_empty IMAGE_TAG "${INPUT_IMAGE_TAG}"
  _exit_if_empty BUILDX_VERSION "${INPUT_BUILDX_VERSION}"
}

install_buildx() {
  buildx_tag=$INPUT_BUILDX_VERSION
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

# pull_cached_stages() {
#   docker pull "$(_get_full_image_name)"-cache:${INPUT_IMAGE_TAG} 2> /dev/null | tee "$PULL_STAGES_LOG" || true
# }

build_image() {
  # max_stage=$(_get_max_stage_number)

  # # create param to use (multiple) --cache-from options
  # if [ "$max_stage" ]; then
  #   cache_from=$(eval "echo --cache-from=$(_get_full_image_name)-stages:{1..$max_stage}")
  #   echo "Use cache: $cache_from"
  # fi

  # build image using cache
  docker build \
    --file=${INPUT_CONTEXT}/${INPUT_DOCKERFILE} \
    --tag="$(_get_full_image_name)":${INPUT_IMAGE_TAG} \
    --push \
    --cache-from="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    --cache-to="$(_get_full_image_name)-cache":${INPUT_IMAGE_TAG} \
    ${INPUT_BUILD_EXTRA_ARGS} \
    ${INPUT_CONTEXT} | tee "$BUILD_LOG"
}

# push_git_tag() {
#   [[ "$GITHUB_REF" =~ /tags/ ]] || return 0
#   local git_tag=${GITHUB_REF##*/tags/}
#   local image_with_git_tag
#   image_with_git_tag="$(_get_full_image_name)":$git_tag
#   docker tag "$(_get_full_image_name)":${INPUT_IMAGE_TAG} "$image_with_git_tag"
#   docker push "$image_with_git_tag"
# }

# push_image_and_stages() {
#   # push image
#   docker push "$(_get_full_image_name)":${INPUT_IMAGE_TAG}
#   push_git_tag

#   # push each building stage
#   stage_number=1
#   for stage in $(_get_stages); do
#     stage_image=$(_get_full_image_name)-stages:$stage_number
#     docker tag "$stage" "$stage_image"
#     docker push "$stage_image"
#     stage_number=$(( stage_number+1 ))
#   done

#   # push the image itself as a stage (the last one)
#   stage_image=$(_get_full_image_name)-stages:$stage_number
#   docker tag "$(_get_full_image_name)":${INPUT_IMAGE_TAG} $stage_image
#   docker push $stage_image
# }

logout_from_registry() {
  docker logout "${INPUT_REGISTRY}"
}

check_required_input
login_to_registry
install_buildx
configure_buildx
#pull_cached_stages
build_image
#push_image_and_stages

logout_from_registry