FROM amazonlinux:latest

ARG PHP_VERSION=5.5

###############################################################################
# Install prereqs
###############################################################################
RUN yum -y update \
    && yum -y install \
    tar \
    git \
    curl \
    sudo \
    # Python
    python3 \
    python3-devel \
    python3-pip \
    make \
    cmake3 \
    gcc \
    gcc-c++ \
    which \
    openssl-devel \
    libcurl-devel \
    libffi-devel \
    libxml2-devel \
    sqlite-devel \
    zlib-devel \
    bzip2 \
    bzip2-devel \
    autoconf \
    automake \
    libtool \
    readline-devel \
    libxslt-devel \
    oniguruma-devel \
    php \
    && yum clean all \
    && rm -rf /var/cache/yum \
    && ln -s /usr/bin/cmake3 /usr/bin/cmake \
    && ln -s /usr/bin/ctest3 /usr/bin/ctest \
    && cmake --version \
    && ctest --version

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install pre-built CMake
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x64.tar.gz -o cmake.tar.gz \
    && tar xzf cmake.tar.gz -C /usr/local \
    && cmake --version \
    && rm -f /tmp/cmake.tar.gz

###############################################################################
# Install composer
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://getcomposer.org/composer-stable.phar -o /usr/local/bin/composer \
    && chmod a+x /usr/local/bin/composer \
    && composer --version

###############################################################################
# Install phpbrew
###############################################################################
WORKDIR /tmp
RUN curl -L -O https://github.com/phpbrew/phpbrew/releases/latest/download/phpbrew.phar \
    && chmod +x phpbrew.phar \
    && mv phpbrew.phar /usr/local/bin/phpbrew \
    && phpbrew init \
    && phpbrew update --old \
    && phpbrew install --stdout -j 4 $PHP_VERSION +small -openssl as $PHP_VERSION \
    && phpbrew switch $PHP_VERSION

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT source /root/.phpbrew/bashrc \
    && /usr/local/bin/builder
