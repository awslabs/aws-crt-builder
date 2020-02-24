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
    && ln -s `find /opt -name aws` /usr/local/bin/aws \
    && which aws \
    && aws --version

###############################################################################
# OpenSSL
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-manylinux2014-x64.tar.gz /opt/openssl
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
#     && rm -rf /tmp/build

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder.pyz /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]