#!/usr/bin/env bash

# This builds libcrypto in the specified container, and uploads the result to S3 for use in building future containers

set -ex

[ $# -eq 3 ]
os=$1
arch=$2
# See ./Configure LIST in openssl
config_platform=$3
libcrypto_version=1.1.1

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

rm -rf /tmp/openssl-${os}-${arch} || true
mkdir -p /tmp/openssl-${os}-${arch}
pushd /tmp/openssl-${os}-${arch}
git clone --single-branch --branch OpenSSL_1_1_1-stable https://github.com/openssl/openssl.git
docker run --rm dockcross/${os}-${arch} > dockcross-${os}-${arch} && chmod a+x dockcross-${os}-${arch}
cd openssl

# Note that commands going into dockcross need to be quoted based on which shell you want the expansion done by. If the
# expansion should be done in the container, make sure the command is single quoted

# Configure OpenSSL
cmd='./Configure '
cmd+=${config_platform}
cmd+=' -fPIC no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng no-unit-test no-tests -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS --prefix=/opt/openssl --openssldir=/opt/openssl'
../dockcross-${os}-${arch} bash -c "$cmd"

# Build, install, tarball install into working directory
cmd='PATH=$PATH:`dirname $CC` make  CC=`basename $CC` AR=`basename $AR` -j && sudo make install_sw && rm -rf install/man'
cmd+=" && tar cvzf /work/libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz -C /opt/openssl ."
# PATH, AR, and CC have to be carefully managed because openssl's configure/make is a little fragile during cross compiles
../dockcross-${os}-${arch} bash -c "$cmd"

# Upload to S3
aws s3 cp libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz s3://aws-crt-builder/_binaries/libcrypto/libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
popd
