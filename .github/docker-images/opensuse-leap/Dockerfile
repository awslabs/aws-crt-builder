FROM opensuse/leap:15.3

SHELL ["/bin/bash", "-c"]

RUN zypper refresh
RUN zypper install -y git gcc gcc-c++ cmake curl python3 python3-pip wget sudo python3-devel tar gzip

# normally we let the builder install this, but the builder does a non-standard install that doesn't play nice
# with opensuse's alternatives framework.  So just install the jdk 11 development package in the base container
# and use it for this particular CI check.
RUN zypper install -y java-11-openjdk-devel

# additional repositories (softhsm)
RUN rpm --import https://download.opensuse.org/repositories/Apache:/Test/openSUSE_Leap_15.2/repodata/repomd.xml.key
RUN zypper ar -f https://download.opensuse.org/repositories/Apache:/Test/openSUSE_Leap_15.2/ ApacheTest

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
