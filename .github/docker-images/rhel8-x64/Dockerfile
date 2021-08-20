FROM registry.access.redhat.com/ubi8/ubi:latest

SHELL ["/bin/bash", "-c"]

RUN dnf install -y gcc gcc-c++ cmake wget python3 python3-pip git make java-1.8.0-openjdk-devel.x86_64 maven
RUN dnf module install -y nodejs:12

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]