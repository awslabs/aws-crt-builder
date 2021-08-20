FROM opensuse/leap:15.2

SHELL ["/bin/bash", "-c"]

RUN zypper refresh && zypper --non-interactive patch
RUN zypper install -y git gcc gcc-c++ cmake curl python3 python3-pip wget nodejs12 java-1_8_0-openjdk-devel maven

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
