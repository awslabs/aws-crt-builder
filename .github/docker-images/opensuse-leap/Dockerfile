FROM opensuse/leap:15.3

SHELL ["/bin/bash", "-c"]

RUN zypper refresh
RUN zypper install -y git gcc gcc-c++ cmake curl python39-devel python39-pip wget sudo tar gzip

# normally we let the builder install this, but the builder does a non-standard install that doesn't play nice
# with opensuse's alternatives framework.  So just install the jdk 11 development package in the base container
# and use it for this particular CI check.
RUN zypper install -y java-11-openjdk-devel

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3.9 -m pip install --upgrade setuptools virtualenv \
    && python3.9 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
