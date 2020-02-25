# See: https://github.com/pypa/manylinux
# and: https://github.com/pypa/python-manylinux-demo
FROM quay.io/pypa/manylinux2014_i686

###############################################################################
# Basics
###############################################################################
RUN yum -y install sudo \
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
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux2014-x86.tar.gz /usr/local

###############################################################################
# Install pre-built libcrypto
###############################################################################
ADD https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-manylinux2014-x86.tar.gz /opt/openssl

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder.pyz /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
