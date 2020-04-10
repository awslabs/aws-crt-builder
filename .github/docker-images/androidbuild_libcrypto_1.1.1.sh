#!/usr/bin/env bash

# This builds libcrypto in the specified container, and uploads the result to S3 for use in building future containers
# Usage: $0 (x86|x86_64|arm64|arm)
set -ex

[ $# -eq 1 ]
[ ! -z $ANDROID_NDK_HOME ]

os=android
arch=$1
# See ./Configure LIST in openssl
config_platform=android-${arch}

libcrypto_version=1.1.1
android_ndk_version=21
android_api_version=21
host_tag=linux-x86_64
toolchain_path=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host_tag

# Note that commands going into dockcross need to be quoted based on which shell you want the expansion done by. If the
# expansion should be done in the container, make sure the command is single quoted

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

mkdir -p /tmp/openssl-${os}-${arch}
pushd /tmp/openssl-${os}-${arch}
if [ ! -d openssl ]; then
    git clone --single-branch --branch OpenSSL_1_1_1-stable https://github.com/openssl/openssl.git
fi

PATH=${toolchain_path}/bin:$PATH
CC=clang

cd openssl

PACKAGE_NAME=libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
./Configure ${config_platform} -D__ANDROID_API__=${android_api_version} -fPIC no-ui-console no-stdio no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng no-unit-test no-tests -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS --prefix=/tmp/openssl-${os}-${arch}/work/opt/openssl --openssldir=/tmp/openssl-${os}-${arch}/work/opt/openssl
make -j
make install_sw
rm -rf /work/opt/openssl/man || true
tar cvzf /tmp/${PACKAGE_NAME} -C /tmp/openssl-${os}-${arch}/work/opt/openssl .

# Upload to S3
aws s3 cp /tmp/libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz s3://aws-crt-builder/_binaries/libcrypto/libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
popd
