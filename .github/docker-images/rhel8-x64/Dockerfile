FROM registry.access.redhat.com/ubi8/ubi:latest

SHELL ["/bin/bash", "-c"]

RUN dnf install -y gcc gcc-c++ cmake wget python3 git make

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]