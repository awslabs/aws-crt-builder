FROM arm64v8/alpine:3.22.8

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
    perl-strictures

# Allow system-wide pip installs, same as --break-system-packages on raspbian-bookworm.
ENV PIP_BREAK_SYSTEM_PACKAGES=1

WORKDIR /tmp

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
