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
    autoconf \
    automake \
    libtool \
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
# Install pre-built OpenSSL
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-linux-x64.tar.gz -o libcrypto.tar.gz \
    && mkdir /opt/openssl \
    && tar xzf libcrypto.tar.gz -C /opt/openssl \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
    && rm -f /tmp/libcrypto.tar.gz

###############################################################################
# Install pre-built CMake
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x64.tar.gz -o cmake.tar.gz \
    && tar xzf cmake.tar.gz -C /usr/local \
    && cmake --version \
    && rm -f /tmp/cmake.tar.gz

###############################################################################
# Build/Install PHP 7.4
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
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
