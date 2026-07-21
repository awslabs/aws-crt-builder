FROM almalinux:8

###############################################################################
# Install prereqs
###############################################################################
RUN yum -y update \
    && yum -y install \
    tar \
    git \
    curl \
    sudo \
    # Python
    python3 \
    python3-devel \
    python3-pip \
    # Build tools
    make \
    gcc \
    gcc-c++ \
    cmake \
    && yum clean all \
    && rm -rf /var/cache/yum \
    && cmake --version \
    && ctest --version

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
