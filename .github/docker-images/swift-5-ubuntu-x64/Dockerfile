# https://github.com/apple/swift-docker/blob/d3a19f47844d7d4d0dab0b59153da1f1596543b6/5.5/ubuntu/16.04/Dockerfile
FROM swift:5.5.2-focal

###############################################################################
# Install prereqs
# any prereqs that appear to be missing are installed on base swift image i.e. tar, git
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    sudo \
    curl \
    wget \
    # Python
    python3 \
    python3-pip \
    # For PPAs
    libssl-dev \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    && apt-get clean

###############################################################################
# Add the corretto repo and public key and install corretto
###############################################################################
RUN wget -O- https://apt.corretto.aws/corretto.key | sudo apt-key add - 
RUN sudo add-apt-repository 'deb https://apt.corretto.aws stable main'
RUN apt-get -y install java-11-amazon-corretto-jdk

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install setuptools \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
