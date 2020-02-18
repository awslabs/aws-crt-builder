FROM arm32v6/alpine AS builder

###############################################################################
# Update apt
###############################################################################
RUN apk --no-cache add build-base

###############################################################################
# Install prereqs
###############################################################################
RUN apk --no-cache add \
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
RUN ([ -d /opt/openssl ] && rm -rf /opt/openssl) || true \
    && git clone https://github.com/openssl/openssl.git \
    && cd openssl \
    && git checkout OpenSSL_1_1_1-stable \
    && ./config -fPIC \
    no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
    no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
    no-unit-test no-tests \
    -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
    --prefix=/opt/openssl --openssldir=/opt/openssl \
    && make -j 2 \
    && make install_sw \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version
# Grab libcrypto that was packed in, from S3, compiled from the above
# COPY openssl-1.1.1.tar.gz /tmp/openssl-1.1.1.tar.gz
# WORKDIR /tmp
# RUN mkdir -p /opt/openssl \
#     && tar xvzf /tmp/openssl-1.1.1.tar.gz -C /opt/openssl \
#     && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version

###############################################################################
# Cleanup
###############################################################################
RUN rm -rf /tmp/*

###############################################################################
# Install builder package
###############################################################################
# ADD builder /usr/local/bin/builder
# COPY entrypoint.sh /entrypoint.sh
# ENTRYPOINT ["/entrypoint.sh"]
