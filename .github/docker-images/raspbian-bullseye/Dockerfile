FROM raspbian/stretch as raspbian-bullseye

###############################################################################
# Upgrade to Bullseye from stretch
###############################################################################

RUN apt-get update \
	&& apt-get upgrade -y \
	&& apt-get full-upgrade -y \
	&& apt-get autoremove --purge -y \
	&& apt-get clean -y \
	# Switch to Bullseye repository.
	&& sed -i 's/stretch/bullseye/g' /etc/apt/sources.list \
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
    cmake \
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
