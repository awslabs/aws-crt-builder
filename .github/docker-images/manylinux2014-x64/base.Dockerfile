# See: https://github.com/pypa/manylinux
# and: https://github.com/pypa/python-manylinux-demo
FROM quay.io/pypa/manylinux2014_x86_64

###############################################################################
# Basics
###############################################################################
RUN yum -y install sudo cmake3 \
    && yum clean all

###############################################################################
# Python/AWS CLI
###############################################################################
RUN /opt/python/cp37-cp37m/bin/python -m pip install --upgrade pip setuptools virtualenv \
    && /opt/python/cp37-cp37m/bin/python -m pip install --upgrade awscli \
    && find /opt -name aws \
    && echo 'export PATH=$PATH:opt/_internal/cpython-3.7.3/bin' >> ~/.login \
    && echo 'export PATH=$PATH:opt/_internal/cpython-3.7.3/bin' >> ~/.bashrc \
    && . ~/.login \
    && aws --version

###############################################################################
# OpenSSL
###############################################################################
WORKDIR /tmp/build
RUN git clone https://github.com/openssl/openssl.git \
    && pushd openssl \
    && git checkout OpenSSL_1_1_1-stable \
    && ./config -fPIC \
    no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
    no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
    no-unit-test no-tests \
    -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
    --prefix=/opt/openssl --openssldir=/opt/openssl \
    && make build_generated && make -j libcrypto.a \
    && make install_sw \
    && rm -rf /tmp/build
