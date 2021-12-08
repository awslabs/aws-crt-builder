FROM amd64/fedora:34

SHELL ["/bin/bash", "-c"]

RUN dnf update -y
RUN dnf install -y make gcc gcc-c++ git cmake curl wget python3 python3-pip

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
