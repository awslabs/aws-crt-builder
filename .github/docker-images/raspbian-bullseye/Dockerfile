FROM raspbian/stretch as raspbian-bullseye

###############################################################################
# Upgrade to buster from stretch
###############################################################################

RUN apt-get update \
	&& apt-get upgrade -y \
	&& apt-get full-upgrade -y \
	&& apt-get autoremove --purge -y \
	&& apt-get clean -y \
	# Switch to Buster repository.
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
# Setup nodejs policy for npm
RUN apt-cache policy nodejs
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    unzip \
    clang \
    cmake \
    # Python
    python3.9 \
    python3-dev \
    python3-pip \
    build-essential \
    # Java Maven
    maven \
    default-jdk \
    # Nodejs
    nodejs \
    npm \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    && apt-get clean


# Override python with python3
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

# Install libs for pythons
RUN sudo apt-get install build-essential checkinstall -y
RUN sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev -y

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python -m pip install --upgrade pip setuptools virtualenv \
    && python -m pip install --upgrade awscli \
    && ln -s `find /opt -name aws` /usr/local/bin/aws \
    && which aws \
    && aws --version



###############################################################################
# Install Python3.6 for Deployment
###############################################################################
WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tgz \
    && tar zxf Python-3.6.0.tgz \
    && cd Python-3.6.0 \
    && ./configure \
    && make -j 4 \
    && make altinstall \
    && python3.6 -m pip install --no-input wheel \
    && cd ..


###############################################################################
# Install Python3.7 for Deployment
###############################################################################
RUN wget https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tgz \
    && tar zxf Python-3.7.0.tgz \
    && cd Python-3.7.0 \
    && ./configure \
    && make -j 4 \
    && make altinstall \
    && python3.7 -m pip install --no-input wheel \
    && cd ..

###############################################################################
# Install Python3.8 for Deployment
###############################################################################
RUN wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz \
    && tar zxf Python-3.8.0.tgz \
    && cd Python-3.8.0 \
    && ./configure \
    && make -j 4 \
    && make altinstall \
    && python3.8 -m pip install --no-input wheel \
    && cd ..


###############################################################################
# Install Python3.10 for Deployment
###############################################################################
RUN wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz \
    && tar zxf Python-3.10.0.tgz \
    && cd Python-3.10.0 \
    && ./configure \
    && make -j 4 \
    && make altinstall \
    && python3.10 -m pip install --no-input wheel \
    && cd ..



###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
