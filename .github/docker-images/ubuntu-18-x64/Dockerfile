FROM ubuntu:18.04

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
    software-properties-common \
    build-essential \
    ca-certificates \
    && apt-get clean

# Install dependencies for building Python from source
RUN apt-get update \
    && apt-get -y install \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
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
    && ln -sf /usr/local/bin/python3.10 /usr/bin/python \
    && /usr/local/bin/python3.10 --version

# Install Go and ensure system Python tools work
RUN apt-get update \
    && apt-get -y install \
    python3-software-properties \
    golang-go

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN /usr/local/bin/python3.10 -m pip install --upgrade pip setuptools virtualenv \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version \
    && rm -rf awscliv2.zip aws

###############################################################################
# Install pre-built CMake
###############################################################################
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x64.tar.gz -o cmake.tar.gz \
    && tar xzf cmake.tar.gz -C /usr/local \
    && cmake --version \
    && rm -f cmake.tar.gz

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
