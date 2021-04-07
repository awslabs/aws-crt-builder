# https://github.com/apple/swift-docker/blob/d3a19f47844d7d4d0dab0b59153da1f1596543b6/5.3/ubuntu/16.04/Dockerfile
FROM swift:5.3-xenial

###############################################################################
# Install prereqs
# any prereqs that appear to be missing are installed on base swift image i.e. tar, git
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    sudo \
    curl \
    # Python
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    # For PPAs
    libssl-dev \
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
