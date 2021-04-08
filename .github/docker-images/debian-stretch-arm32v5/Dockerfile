FROM arm32v5/debian:stretch-slim

RUN apt-get update -y \
    && apt-get dist-upgrade -y \
    && apt-get install -y \
        sudo \
        ca-certificates \
        build-essential \
        curl \
        cmake \
        git \
        python3-dev \
        python3-pip \
    && cmake --version \
    && ctest --version

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN python3 -m pip install setuptools \
    && python3 -m pip install --upgrade pip \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
