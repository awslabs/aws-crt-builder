#!/bin/bash
# $1 - TARGET_ARCH

set -e
TARGET_ARCH=$1
shift

aws ecr get-login-password | docker login 123124136734.dkr.ecr.us-east-1.amazonaws.com -u AWS --password-stdin
docker run --rm --privileged aws-crt-aptman-qus -s -- -p $TARGET_ARCH
