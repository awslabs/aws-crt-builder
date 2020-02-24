FROM raspbian/stretch

ENV DEBIAN_FRONTEND=noninteractive

###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update \
    && apt-get install -y \
    git \
    curl \
    libssl-dev \
    # Python
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    cmake \
    # For PPAs
    software-properties-common \
    apt-transport-https	\
    && apt-get clean

# ###############################################################################
# # Python/AWS CLI
# ###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# OpenSSL
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-raspbian-armv6.tar.gz /opt/openssl
# WORKDIR /tmp/build
# RUN git clone https://github.com/openssl/openssl.git \
#     && cd openssl \
#     && git checkout OpenSSL_1_1_1-stable \
#     && ./config -fPIC \
#     no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 \
#     no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng \
#     no-unit-test no-tests \
#     -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS \
#     --prefix=/opt/openssl --openssldir=/opt/openssl \
#     && make build_generated && make -j 3 libcrypto.a \
#     && make install_sw \
#     && rm -rf /tmp/build

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder.pyz /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
