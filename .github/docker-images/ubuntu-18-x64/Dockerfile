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

# Add PPAs with retry
RUN add-apt-repository -y ppa:deadsnakes/ppa \
    && add-apt-repository -y ppa:longsleep/golang-backports \
    && apt-get update

# Install Python 3.10 and Go
RUN apt-get -y install \
    python3.10-dev \
    python3.10-venv \
    python3.10-distutils \
    golang-go \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python3.10 get-pip.py \
    && python3.10 -m pip install setuptools \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version \
    && rm -rf get-pip.py awscliv2.zip aws

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
