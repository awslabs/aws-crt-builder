FROM registry.access.redhat.com/ubi8/ubi:latest

SHELL ["/bin/bash", "-c"]

RUN dnf install -y \
    gcc \
    gcc-c++ \
    cmake \
    wget \
    git \
    make \
    sudo \
    # RHEL8's default python3 is python3.6, which is EOL.
    # So install python3.9 (latest version on this distro, circa Oct 2022)
    python39-devel

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
