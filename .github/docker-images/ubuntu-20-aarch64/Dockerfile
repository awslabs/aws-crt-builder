FROM arm64v8/ubuntu:focal

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
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    cmake

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

# this image comes with gcc9.3 which current version of aws-lc rejects
RUN curl -L https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add - \
    && add-apt-repository ppa:ubuntu-toolchain-r/test \
    && apt-add-repository "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-11 main" \
    && apt-get update -y \
    && apt-get install clang-11 cmake -y -f \
    && apt-get clean

ENV CC=clang-11

RUN python3 -m pip install setuptools \
    && python3 -m pip install --upgrade pip \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
