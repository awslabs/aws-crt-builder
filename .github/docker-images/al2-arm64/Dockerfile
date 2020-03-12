FROM arm64v8/amazonlinux:latest


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
    maven \
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
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-al2-arm64.tar.gz -o libcrypto.tar.gz \
    && mkdir /opt/openssl \
    && tar xzf libcrypto.tar.gz -C /opt/openssl \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
    && rm -f /tmp/libcrypto.tar.gz

###############################################################################
# Install node binaries
###############################################################################
RUN curl -sSL https://nodejs.org/download/release/latest-v10.x/node-v10.19.0-linux-arm64.tar.gz -o node.tar.gz \
    && tar xzf node.tar.gz \
    && cd node-v* \
    && cp -r share/* /usr/local/share \
    && cp -r lib/* /usr/local/lib \
    && cp -r bin/* /usr/local/bin \
    && cp -r include/* /usr/local/include \
    && node --version \
    && rm -rf /tmp/node*

###############################################################################
# Maven cache/settings
###############################################################################
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/maven/maven-al2-arm64.tar.gz -o maven.tar.gz \
    && mkdir -p /root/.m2 \
    && tar xzf maven.tar.gz -C /root/.m2 \
    && rm -f /tmp/maven.tar.gz
ADD maven_settings.xml /root/.m2/settings.xml

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
