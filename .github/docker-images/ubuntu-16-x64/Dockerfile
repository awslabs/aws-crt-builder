FROM ubuntu:16.04


###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    git \
    curl \
    sudo \
    # Python
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    cmake \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    && apt-get clean

##############################################################################
# Docker (for cross compiling via dockcross)
###############################################################################
WORKDIR /tmp
RUN set -ex && curl -fsSL https://get.docker.com -o /tmp/get-docker.sh \
    && sh /tmp/get-docker.sh \
    && systemctl enable docker \
    && echo "service docker start" >> ~/.bashrc

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install pre-built libcrypto
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-ubuntu-16-x64.tar.gz -o libcrypto.tar.gz \
    && mkdir /opt/openssl \
    && tar xzf libcrypto.tar.gz -C /opt/openssl \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
    && rm -f /tmp/libcrypto.tar.gz

###############################################################################
# Install entrypoint
###############################################################################
# ADD entrypoint.sh /usr/local/bin/builder
# RUN chmod a+x /usr/local/bin/builder
# ENTRYPOINT ["/usr/local/bin/builder"]
