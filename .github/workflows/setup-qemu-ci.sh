#!/bin/bash
# $1 - TARGET_ARCH

set -ex
TARGET_ARCH=$1
shift

aws ecr get-login-password | docker login 123124136734.dkr.ecr.us-east-1.amazonaws.com -u AWS --password-stdin
# Get around docker pull limitation error by log into docker. So that we can get 5000 limit within 24 hours instead of 100.
docker run --rm --privileged aptman/qus -s -- -p $TARGET_ARCH
