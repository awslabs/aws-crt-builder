FROM raspbian/stretch

ENV DEBIAN_FRONTEND=noninteractive

###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update \
    && apt-get install -y \
    git \
    curl \
    libssl-dev \
    # Python
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    cmake \
    maven \
    # For PPAs
    software-properties-common \
    apt-transport-https	\
    && apt-get clean

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install pre-built libcrypto
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-raspbian-armv7.tar.gz -o libcrypto.tar.gz \
    && mkdir /opt/openssl \
    && tar xzf libcrypto.tar.gz -C /opt/openssl \
    && LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/openssl/lib /opt/openssl/bin/openssl version \
    && rm -f /tmp/libcrypto.tar.gz

###############################################################################
# Maven settings
###############################################################################
ADD settings.xml /root/.m2/settings.xml
ADD https://raw.githubusercontent.com/awslabs/aws-crt-java/master/pom.xml pom.xml
RUN mvn dependency:go-offline -B --fail-never && rm -rf /tmp/maven

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder.pyz /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
