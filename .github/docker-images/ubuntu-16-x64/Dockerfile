FROM ubuntu:16.04

ENV DEBIAN_FRONTEND=noninteractive

###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    # Python
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    && apt-get clean

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install setuptools \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install pre-built CMake
###############################################################################
WORKDIR /tmp
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
