FROM scratch
ADD http://os.archlinuxarm.org/os/ArchLinuxARM-rpi-latest.tar.gz /

###############################################################################
# Install prereqs
###############################################################################
RUN pacman -Svuy --noconfirm \
    git \
    curl \
    python \
    python-pip \
    cmake \
    make \
    openssl \
    linux-api-headers \
    && pacman -Scc

###############################################################################
# Python/AWS CLI
###############################################################################
RUN python3 -m pip install --upgrade pip setuptools virtualenv \
    && python3 -m pip install --upgrade awscli \
    && aws --version

