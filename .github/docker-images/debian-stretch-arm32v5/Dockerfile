FROM arm32v5/debian:stretch-slim

RUN apt-get update -y \
    && apt-get dist-upgrade -y \
    && apt-get install -y \
        sudo \
        ca-certificates \
        build-essential \
        curl \
        cmake \
        git \
    && cmake --version \
    && ctest --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
