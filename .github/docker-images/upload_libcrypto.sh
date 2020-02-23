#!/usr/bin/env bash

set -ex

[ $# -eq 4 ]
variant=$1
arch=$2
version=$3
libcrypto_version=$4

if [ ! -e /tmp/aws-crt-${variant}-${arch}-${version}.tar ]; then
    aws s3 cp s3://aws-crt-builder/_docker/aws-crt-${variant}-${arch}-${version}.tar /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}-${version}.tar
fi
container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version} sh)
docker exec ${container} tar czf /tmp/libcrypto-${libcrypto_version}-${variant}-${arch}.tar.gz -C /opt/openssl .
docker exec ${container} aws s3 cp /tmp/libcrypto-${libcrypto_version}-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/libcrypto/libcrypto-${libcrypto_version}-${variant}-${arch}.tar.gz
docker stop ${container}