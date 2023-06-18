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
    # Python
    python3 \
    python3-dev \
    py3-pip \
    build-base \
    linux-headers \
    ca-certificates \
    cmake \
    bash \
    aws-cli \
    coreutils

WORKDIR /tmp

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
