#!/usr/bin/env bash

set -ex

[ $# -eq 3 ]
variant=$1
arch=$2
version=$3
cmake_version=3.13

if [ ! -e /tmp/aws-crt-${variant}-${arch}-${version}.tar ]; then
    aws s3 cp s3://aws-crt-builder/_docker/aws-crt-${variant}-${arch}-${version}.tar /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}-${version}.tar
fi
container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version} sh)
docker exec ${container} tar czf /tmp/cmake-${cmake_version}-${variant}-${arch}.tar.gz -C /usr/local \
    share/cmake-${cmake_version} bin/cmake bin/ctest bin/cpack doc/cmake-${cmake_version}
docker exec ${container} aws s3 cp /tmp/cmake-${cmake_version}-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/cmake/cmake-${cmake_version}-${variant}-${arch}.tar.gz
docker stop ${container}