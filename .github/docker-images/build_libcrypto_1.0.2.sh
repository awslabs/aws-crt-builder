#!/usr/bin/env bash

# This builds libcrypto in the specified container, and uploads the result to S3 for use in building future containers

set -ex

[ $# -eq 3 ]
variant=$1
arch=$2
version=$3
libcrypto_version=1.0.2

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

if [ ! -e /tmp/aws-crt-${variant}-${arch}.tar.gz ]; then
    aws s3 cp s3://aws-crt-builder/${version}/aws-crt-${variant}-${arch}.tar.gz /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}.tar.gz
fi

container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint /bin/sh docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version})
docker exec ${container} sh -c "rm -rf /opt/openssl; cd /tmp && git clone --single-branch --branch OpenSSL_1_0_2-stable https://github.com/openssl/openssl.git"
docker exec ${container} sh -c "cd /tmp/openssl && ./config -fPIC \
    no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
    no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
    no-unit-test no-tests \
    -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
    --prefix=/opt/openssl --openssldir=/opt/openssl"
docker exec ${container} sh -c "cd /tmp/openssl && make depend"
docker exec ${container} sh -c "cd /tmp/openssl && make -j && make install_sw"
docker exec ${container} sh -c "tar czf /tmp/libcrypto-${libcrypto_version}-${variant}-${arch}.tar.gz -C /opt/openssl ."
docker exec ${container} sh -c "aws s3 cp /tmp/libcrypto-${libcrypto_version}-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/libcrypto/libcrypto-${libcrypto_version}-${variant}-${arch}.tar.gz"
docker stop ${container}
