#https://github.com/apple/swift-docker/blob/d3a19f47844d7d4d0dab0b59153da1f1596543b6/5.5/centos/7/Dockerfile
FROM swift:5.5-centos7

###############################################################################
# Install prereqs
# any prereqs that appear to be missing are installed on base swift image i.e. tar, git
###############################################################################
RUN yum -y install \
    sudo \
    # Python
    python3 \
    python3-pip \
    openssl-devel \
    make \
    libcurl-devel \
    && yum clean all \
    && rm -rf /var/cache/yum

###############################################################################
# Fix the old version of git on CentOS which SPM can't work with
###############################################################################
RUN git clone https://github.com/git/git -bv2.33.1 --depth 1 && cd git
RUN make prefix=/usr -j all install NO_OPENSSL=1 NO_EXPAT=1 NO_TCLTK=1 NO_GETTEXT=1 NO_PERL=1

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
