
BUILDX_VERSION=v0.3.1

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
  docker buildx create --name builder --driver docker --use
  docker buildx inspect --bootstrap
  docker buildx install
}

install_buildx
configure_buildx
