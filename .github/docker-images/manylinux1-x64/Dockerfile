# See: https://github.com/pypa/manylinux	FROM docker.pkg.github.com/awslabs/aws-crt-python/manylinux1:x64
# and: https://github.com/pypa/python-manylinux-demo
FROM quay.io/pypa/manylinux1_x86_64

###############################################################################
# Basics
###############################################################################
RUN yum -y install sudo \
    && yum clean all

###############################################################################
# Python/AWS CLI
###############################################################################
RUN /opt/python/cp37-cp37m/bin/python -m pip install --upgrade setuptools virtualenv \
    && /opt/python/cp37-cp37m/bin/python -m pip install --upgrade awscli \
    && ln -s `find /opt -name aws` /usr/local/bin/aws \
    && which aws \
    && aws --version

###############################################################################
# Install pre-built CMake
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x64.tar.gz -o cmake.tar.gz \
    && tar xvzf cmake.tar.gz -C /usr/local \
    && cmake --version \
    && rm -f /tmp/cmake.tar.gz

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
