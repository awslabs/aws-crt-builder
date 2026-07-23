# See: https://github.com/pypa/manylinux
# and: https://github.com/pypa/python-manylinux-demo
# manylinux_2_28 is based on AlmaLinux 8 (glibc 2.28)
FROM quay.io/pypa/manylinux_2_28_aarch64

###############################################################################
# Basics
###############################################################################
# cmake and ctest come pre-installed via pipx in manylinux_2_28
RUN yum -y install sudo \
    && yum clean all \
    && cmake --version \
    && ctest --version

###############################################################################
# Python/AWS CLI
###############################################################################
RUN /opt/python/cp39-cp39/bin/python -m pip install --upgrade setuptools virtualenv \
    && /opt/python/cp39-cp39/bin/python -m pip install --upgrade awscli \
    && ln -s `find /opt -name aws` /usr/local/bin/aws \
    && which aws \
    && aws --version

###############################################################################
# nodejs/npm
###############################################################################
RUN curl -sL https://rpm.nodesource.com/setup_18.x | bash -
RUN yum -y install nodejs && node --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
