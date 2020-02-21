#!/usr/bin/env bash

set -ex

workdir=`pwd`
git clone https://github.com/openssl/openssl.git
cd openssl
git checkout OpenSSL_1_0_2-stable
./config -fPIC \
    no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
    no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
    no-unit-test no-tests \
    -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
    --prefix=/opt/openssl --openssldir=/opt/openssl
make -j depend
make -j
make install_sw
rm -rf $workdir