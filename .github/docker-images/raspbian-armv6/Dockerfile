# This image is in S3, built from Dockerfile.bootstrap in this directory
FROM docker.pkg.github.com/awslabs/aws-crt-builder/raspbian-armv6 as builder

SHELL ["/bin/bash", "-c"]

###############################################################################
# Install prereqs
###############################################################################
RUN DEBIAN_FRONTEND=noninteractive \
    sed -i 's/jessie/buster/' /etc/apt/sources.list \
    && apt-get update -y \
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
    apt-transport-https

# ###############################################################################
# # Python/AWS CLI
# ###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# OpenSSL
###############################################################################
# COPY openssl-1.1.1.tar.gz /tmp/openssl-1.1.1.tar.gz
# WORKDIR /tmp
# RUN mkdir -p /opt/openssl \
#     && tar xvzf /tmp/openssl-1.1.1.tar.gz -C /opt/openssl \
#     && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version

###############################################################################
# Cleanup
###############################################################################
RUN apt-get clean \
    && rm -rf /tmp/*

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
