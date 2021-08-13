FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

ENV ANDROID_SDK_HOME /opt/android-sdk
ENV ANDROID_SDK_ROOT /opt/android-sdk
ENV ANDROID_HOME /opt/android-sdk
ENV ANDROID_SDK /opt/android-sdk

###############################################################################
# Install prereqs
###############################################################################
# NOTE: Latest Android tooling requires jdk11+
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    unzip \
    python3 \
    python3-dev \
    python3-pip \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    cmake \
    openjdk-11-jdk

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN python3 -m pip install setuptools \
    && python3 -m pip install --upgrade pip \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version

###############################################################################
# Android SDK
###############################################################################

# install SDK tools
RUN curl "https://dl.google.com/android/repository/commandlinetools-linux-7583922_latest.zip" -o android-cli.zip \
 && mkdir -p $ANDROID_HOME/cmdline-tools/latest \
 && unzip android-cli.zip -d cli-tools \
 && mv cli-tools/cmdline-tools/* $ANDROID_HOME/cmdline-tools/latest \
 && rm -rf cli-tools \
 && rm android-cli.zip


RUN mkdir -p ~/.android && touch ~/.android/repositories.cfg
RUN echo y | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --install "build-tools;30.0.3" "platforms;android-30" "ndk;21.4.7075529" "cmake;3.10.2.4988404"


###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]
