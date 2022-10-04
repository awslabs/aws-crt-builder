FROM raspbian/stretch as raspbian-buster

###############################################################################
# Upgrade to buster from stretch
###############################################################################

RUN apt-get update \
	&& apt-get upgrade -y \
	&& apt-get full-upgrade -y \
	&& apt-get autoremove --purge -y \
	&& apt-get clean -y \
	# Switch to Buster repository.
	&& sed -i 's/stretch/buster/g' /etc/apt/sources.list \
	# Update all packages.
	&& apt-get update \
	&& apt-get upgrade -y \
	&& apt-get full-upgrade -y \
	&& apt-get autoremove --purge -y \
	&& apt-get clean -y

###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    unzip \
    clang \
    # Python
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    && apt-get clean

# Override python with python3
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

###############################################################################
# Install CMake3.19 to avoid Remove-Item issue with CMake < 3.19
###############################################################################
WORKDIR /tmp
RUN wget https://cmake.org/files/v3.19/cmake-3.19.0.tar.gz \
    && tar -xvzf cmake-3.19.0.tar.gz \
    && cd cmake-3.19.0/ \
    && sudo ./bootstrap \
    && sudo make \
    && sudo make install

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python -m pip install --upgrade pip setuptools virtualenv \
    && python -m pip install --upgrade awscli \
    && ln -s `find /opt -name aws` /usr/local/bin/aws \
    && which aws \
    && aws --version


###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]