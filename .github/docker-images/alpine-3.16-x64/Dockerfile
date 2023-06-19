FROM amd64/alpine:3.16.2

###############################################################################
# Install prereqs
###############################################################################
RUN apk update
RUN apk add \
    git \
    curl \
    sudo \
    unzip \
    python3 \
    python3-dev \
    py3-pip \
    build-base \
    linux-headers \
    ca-certificates \
    cmake \
    aws-cli \
    coreutils \
    openssl \
    ncurses \
    make \
    gcc \
    g++ \
    libgcc \
    grep \
    util-linux \
    binutils \
    findutils \
    gcompat

# Create bashrc directory
RUN touch ~/.profile && chmod +x ~/.profile

WORKDIR /tmp

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
