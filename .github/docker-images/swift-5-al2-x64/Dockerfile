#https://github.com/apple/swift-docker/blob/d3a19f47844d7d4d0dab0b59153da1f1596543b6/5.5/amazonlinux/2/Dockerfile
FROM swift:5.7.0-amazonlinux2

###############################################################################
# Install prereqs
# any prereqs that appear to be missing are installed on base swift image i.e. tar, git
###############################################################################
RUN yum -y install \
    curl \
    sudo \
    # Python
    python3 \
    python3-pip \
    openssl-devel \
    && yum clean all \
    && rm -rf /var/cache/yum

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
