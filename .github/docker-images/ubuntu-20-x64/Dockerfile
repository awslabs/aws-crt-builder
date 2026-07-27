FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    unzip \
    python3-dev \
    python3-pip \
    build-essential \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    && apt-get clean

# Add the longsleep/golang-backports PPA
RUN apt-get update && apt-get install -y software-properties-common && add-apt-repository ppa:longsleep/golang-backports && apt-get update

# Install Go from the PPA
RUN apt-get install -y golang-go

# Install dependencies for building Python from source
# Ubuntu 20.04 ships Python 3.8 by default, but the builder requires Python 3.10
# (builder/core/data.py maps every ubuntu host to the "python3.10" interpreter), so
# we build 3.10 from source below.
RUN apt-get update \
    && apt-get -y install \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev

# Build Python 3.10 from source
RUN cd /tmp \
    && curl -O https://www.python.org/ftp/python/3.10.12/Python-3.10.12.tgz \
    && tar -xzf Python-3.10.12.tgz \
    && cd Python-3.10.12 \
    && ./configure --with-ensurepip=install \
    && make -j$(nproc) \
    && make altinstall \
    && cd / \
    && rm -rf /tmp/Python-3.10.12* \
    && ln -sf /usr/local/bin/python3.10 /usr/local/bin/python \
    && ln -sf /usr/local/bin/python3.10 /usr/local/bin/python3 \
    && /usr/local/bin/python3.10 --version

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN /usr/local/bin/python3.10 -m pip install --upgrade pip setuptools virtualenv \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version

###############################################################################
# Install pre-built CMake
###############################################################################
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x64.tar.gz -o cmake.tar.gz \
    && tar xvzf cmake.tar.gz -C /usr/local \
    && cmake --version \
    && rm -f /tmp/cmake.tar.gz

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
