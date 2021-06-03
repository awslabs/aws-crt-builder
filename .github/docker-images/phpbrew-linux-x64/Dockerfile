FROM amazonlinux:latest

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
# Build/Install PHP 7.4 as system PHP
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://www.php.net/distributions/php-7.4.15.tar.gz -o php.tar.gz \
    && tar xzf php.tar.gz \
    && cd php-7.4.15 \
    && ./configure --prefix=/usr/local --disable-cgi --with-openssl --with-ffi --with-curl --with-zlib \
    && make -j \
    && make install

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
    && cat ~/.phpbrew/bashrc >> /etc/environment

RUN phpbrew install -j 4 5.5 +small -openssl as 5.5
RUN phpbrew install -j 4 5.6 +small -openssl as 5.6
RUN phpbrew install -j 4 7.0 +small -openssl as 7.0
RUN phpbrew install -j 4 7.1 +small -openssl as 7.1
RUN phpbrew install -j 4 7.2 +small -openssl as 7.2
RUN phpbrew install -j 4 7.3 +small -openssl as 7.3
RUN phpbrew install -j 4 7.4 +small -openssl as 7.4
RUN phpbrew install -j 4 8.0 +small -openssl as 8.0

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
