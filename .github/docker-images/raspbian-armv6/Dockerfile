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
# Install pre-built libcrypto
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-raspbian-armv6.tar.gz /opt/openssl

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder.pyz /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
