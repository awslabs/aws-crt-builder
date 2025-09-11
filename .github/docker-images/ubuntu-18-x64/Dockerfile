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
    # Ubuntu18's default python3 is python3.6, we will install Python 3.10
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get -y install \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    build-essential \
    apt-transport-https \
    ca-certificates \
    && apt-get clean \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3

# Add the longsleep/golang-backports PPA
RUN apt-get update && apt-get install -y software-properties-common && add-apt-repository ppa:longsleep/golang-backports && apt-get update

# Install Go from the PPA
RUN apt-get install -y golang-go

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN python3 -m pip install setuptools \
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
