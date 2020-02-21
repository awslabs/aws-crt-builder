FROM arm32v7/alpine

###############################################################################
# Install prereqs
###############################################################################
RUN apk --no-cache add \
    build-base \
    git \
    curl \
    sudo \
    python3-dev \
    cmake \
    clang \
    perl \
    linux-headers

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# OpenSSL
###############################################################################
WORKDIR /tmp/build
RUN git clone https://github.com/openssl/openssl.git \
    && cd openssl \
    && git checkout OpenSSL_1_1_1-stable \
    && ./config -fPIC \
    no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
    no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
    no-unit-test no-tests \
    -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
    --prefix=/opt/openssl --openssldir=/opt/openssl \
    && make -j 3 \
    && make install_sw \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
    && rm -rf /tmp/build

