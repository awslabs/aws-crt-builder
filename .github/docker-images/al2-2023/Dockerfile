FROM amazonlinux:2023


###############################################################################
# Install prereqs
###############################################################################
RUN yum -y update \
    && yum -y install \
    tar \
    git \
    sudo \
    # Python
    python3 \
    python3-devel \
    python3-pip \
    make \
    cmake3 \
    gcc \
    gcc-c++ \
    which \
    && yum clean all \
    && rm -rf /var/cache/yum \
    && cmake --version \
    && ctest --version

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install setuptools virtualenv \
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
