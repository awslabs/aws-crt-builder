FROM amazonlinux:latest


###############################################################################
# Install prereqs
###############################################################################
RUN yum -y update \
    && yum -y install \
    tar \
    git \
    curl \
    sudo \
    # Python
    python3 \
    python3-devel \
    python3-pip \
    make \
    cmake3 \
    gcc \
    gcc-c++ \
    && yum clean all \
    && rm -rf /var/cache/yum \
    && ln -s /usr/bin/cmake3 /usr/bin/cmake \
    && ln -s /usr/bin/ctest3 /usr/bin/ctest \
    && cmake --version \
    && ctest --version

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# OpenSSL
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-al2-x64.tar.gz /opt/openssl
# WORKDIR /tmp/build
# RUN git clone https://github.com/openssl/openssl.git \
#     && pushd openssl \
#     && git checkout OpenSSL_1_1_1-stable \
#     && ./config -fPIC \
#     no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
#     no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
#     no-unit-test no-tests \
#     -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
#     --prefix=/opt/openssl --openssldir=/opt/openssl \
#     && make build_generated && make -j libcrypto.a \
#     && make install_sw \
#     && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
#     && rm -rf /tmp/*
