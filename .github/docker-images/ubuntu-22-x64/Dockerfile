FROM ubuntu:22.04

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
    golang-go \
    && apt-get clean

# ubuntu-toolchain-r PPA provides newer gcc versions
RUN apt-add-repository -y ppa:ubuntu-toolchain-r/test

# Bake the apt.llvm.org key so parallel CI jobs don't fetch it at runtime.
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused --connect-timeout 15 \
        https://apt.llvm.org/llvm-snapshot.gpg.key \
        -o /etc/apt/trusted.gpg.d/apt.llvm.org.asc \
    && test -s /etc/apt/trusted.gpg.d/apt.llvm.org.asc

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
