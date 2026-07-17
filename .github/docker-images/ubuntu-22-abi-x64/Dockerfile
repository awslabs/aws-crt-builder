FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

###############################################################################
# Install prereqs + the ABI toolchain.
#
# Baking abi-compliance-checker / abi-dumper / universal-ctags into the image is
# the whole point of this variant: the check-abi action used to apt-get install
# them on every CI run. cmake and build-essential are here because building the
# CRT shared libs (via builder.pyz) needs them.
#
# libssl-dev is intentionally NOT installed: ubuntu:22.04 ships libssl3 (the
# runtime .so) by default, just not the -dev headers/pkg-config. Untested
# whether any lib-name build in check-abi actually needs the headers -- if a
# build fails here looking for <openssl/*.h> or openssl.pc, add it back.
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    unzip \
    python3-dev \
    python3-pip \
    build-essential \
    # cmake via apt (Ubuntu 22.04 ships 3.22.1, above aws-c-common's >=3.9
    # floor) instead of a hand-downloaded tarball: apt verifies the package
    # against Ubuntu's signed repo metadata, so there's no separate checksum
    # to source, trust, or keep in sync ourselves.
    cmake \
    # ABI toolchain
    abi-compliance-checker \
    abi-dumper \
    universal-ctags \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    && apt-get clean

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

# nh3 sanitizes the abi-compliance-checker HTML report (which embeds
# attacker-controlled symbol/type names from the PR's own source) before
# report.py writes it into $GITHUB_STEP_SUMMARY -- see report.py.
RUN python3 -m pip install setuptools nh3 \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
