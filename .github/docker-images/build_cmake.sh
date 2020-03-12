#!/usr/bin/env bash

# This builds CMake in the specified container, and uploads the result to S3 for use in building future containers

set -ex

[ $# -eq 4 ]
variant=$1
arch=$2
version=$3

# 3.13.5 is the last version to work with ancient glibc
CMAKE_VERSION=3.13.5

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

if [ ! -e /tmp/aws-crt-${variant}-${arch}.tar.gz ]; then
    aws s3 cp s3://aws-crt-builder/${version}/aws-crt-${variant}-${arch}.tar.gz /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}.tar.gz
fi

container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint /bin/sh docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version})
docker exec ${container} sh -c "cd /tmp && curl -LO https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}.tar.gz"
docker exec ${container} sh -c "cd /tmp && tar xzf cmake-${CMAKE_VERSION}.tar.gz && cd cmake-${CMAKE_VERSION} && ./bootstrap -- -DCMAKE_BUILD_TYPE=Release"
docker exec ${container} sh -c "cd /tmp/cmake-${CMAKE_VERSION} && make -j && make install"
docker exec ${container} sh -c "tar czf /tmp/cmake-${CMAKE_VERSION}-${variant}-${arch}.tar.gz -C /usr/local share/cmake-${CMAKE_VERSION} bin/cmake bin/ctest bin/cpack doc/cmake-${CMAKE_VERSION}"
docker exec ${container} sh -c "aws s3 cp /tmp/cmake-${CMAKE_VERSION}-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/cmake/cmake-${CMAKE_VERSION}-${variant}-${arch}.tar.gz"
docker stop ${container}
