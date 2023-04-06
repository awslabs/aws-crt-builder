# https://hub.docker.com/_/swift
FROM swift:5.5.3-amazonlinux2

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
RUN python3 -m pip install --upgrade setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
