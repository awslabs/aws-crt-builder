# See: https://github.com/pypa/manylinux	FROM docker.pkg.github.com/awslabs/aws-crt-python/manylinux1:x64
# and: https://github.com/pypa/python-manylinux-demo	
FROM quay.io/pypa/manylinux1_x86_64	

# 3.13.5 is the last version to work with ancient glibc	
ENV CMAKE_VERSION=3.13.5	

###############################################################################	
# Basics
###############################################################################	
RUN yum -y update \ 
    && yum -y install sudo \
    && yum clean all

###############################################################################	
# CMake	
###############################################################################	
WORKDIR /tmp/build
RUN curl -LO https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}.tar.gz \	
    && tar xzf cmake-${CMAKE_VERSION}.tar.gz \	
    && cd cmake-${CMAKE_VERSION} \	
    && ./bootstrap -- -DCMAKE_BUILD_TYPE=Release \	
    && make \	
    && make install \	
    && cmake --version \
    && rm -rf /tmp/build

###############################################################################	
# OpenSSL	
###############################################################################	
WORKDIR /tmp/build
RUN git clone https://github.com/openssl/openssl.git \
    && pushd openssl \
    && git checkout OpenSSL_1_0_2-stable \
    && ./config -fPIC \
    no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
    no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
    no-unit-test no-tests \
    -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
    --prefix=/opt/openssl --openssldir=/opt/openssl \
    && make build_generated && make -j \
    && make install_sw \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
    && rm -rf /tmp/build
