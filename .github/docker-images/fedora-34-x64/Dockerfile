FROM amd64/fedora:34

SHELL ["/bin/bash", "-c"]

RUN dnf update -y
RUN dnf install -y make gcc gcc-c++ git cmake curl wget python3 python3-pip java-1.8.0-openjdk-devel.x86_64 maven
RUN dnf module install -y nodejs:12


###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
