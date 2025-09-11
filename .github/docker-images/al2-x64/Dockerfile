FROM amazonlinux:2


###############################################################################
# Install prereqs
###############################################################################
RUN yum -y update \
    # We bumped min supported version of Python to 3.8.
    # AL2 installs 3.7 when using python3-devel
    && amazon-linux-extras install python3.8 -y \
    && yum -y install \
    tar \
    git \
    sudo \ 
    python38-devel \
    make \
    gcc \
    gcc-c++ \
    which \
    && yum clean all \
    && rm -rf /var/cache/yum
    # insure python3 and pip3 point to python3.8
    && ln -sf /usr/bin/python3.8 /usr/bin/python3 \
    && ln -sf /usr/bin/pip3.8 /usr/bin/pip3

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install pre-built CMake
###############################################################################
WORKDIR /tmp
RUN curl -sSL https://d19elf31gohf1l.cloudfront.net/_binaries/cmake/cmake-3.13-manylinux1-x64.tar.gz -o cmake.tar.gz \
    && tar xvzf cmake.tar.gz -C /usr/local \
    && cmake --version \
    && ctest --version \
    && rm -f /tmp/cmake.tar.gz

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
