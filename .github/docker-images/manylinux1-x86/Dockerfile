# See: https://github.com/pypa/manylinux	FROM docker.pkg.github.com/awslabs/aws-crt-python/manylinux1:x86
# and: quay.io/pypa/manylinux1_x86_64
FROM quay.io/pypa/manylinux1_i686

###############################################################################
# Basics
###############################################################################
RUN yum -y update \
    && yum -y install sudo \
    && yum clean all

###############################################################################
# Python/AWS CLI
###############################################################################
RUN /opt/python/cp37-cp37m/bin/python -m pip install --upgrade pip setuptools virtualenv \
    && /opt/python/cp37-cp37m/bin/python -m pip install --upgrade awscli \
    && ln -s `find /opt -name aws` /usr/local/bin/aws \
    && which aws \
    && aws --version

###############################################################################
# Install pre-built CMake
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x86.tar.gz /usr/local

###############################################################################
# Install pre-built libcrypto
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-manylinux1-x86.tar.gz /opt/openssl

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder.pyz /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
