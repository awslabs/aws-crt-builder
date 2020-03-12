#!/usr/bin/env bash

# This builds nodejs in the specified container, and uploads the result to S3 for use in building future containers

set -ex

[ $# -eq 3 ]
variant=$1
arch=$2
version=$3
nodejs_version=10.19.0

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

if [ ! -e /tmp/aws-crt-${variant}-${arch}.tar.gz ]; then
    aws s3 cp s3://aws-crt-builder/${version}/aws-crt-${variant}-${arch}.tar.gz /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}.tar.gz
fi

container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint /bin/sh docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version})
docker exec ${container} sh -c "cd /tmp && curl -sSLO https://nodejs.org/download/release/latest-v10.x/node-v${nodejs_version}-linux-x64.tar.gz"
docker exec ${container} sh -c "cd /tmp && tar xvzf node-v${nodejs_version}-linux-x64.tar.gz"
docker exec ${container} sh -c "cd /tmp/node-v${nodejs_version}-linux-x64 && ./configure"
docker exec ${container} sh -c "cd /tmp/node-v${nodejs_version}-linux-x64 && make -j"
docker exec ${container} sh -c "cd /tmp/node-v${nodejs_version}-linux-x64 && make install PREFIX=/opt/nodejs"
docker exec ${container} sh -c "tar czf /tmp/nodejs-${nodejs_version}-${variant}-${arch}.tar.gz -C /opt/nodejs ."
docker exec ${container} sh -c "aws s3 cp /tmp/nodejs-${nodejs_version}-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/nodejs/nodejs-${nodejs_version}-${variant}-${arch}.tar.gz"
docker stop ${container}
