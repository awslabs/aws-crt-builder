#!/usr/bin/env bash

# This clones aws-crt-java in the specified container, builds it with maven, then caches maven's respository to S3

set -ex

[ $# -ge 3 ]
variant=$1
arch=$2
version=$3

crt_java_branch=master
if [ $# -gt 3 ]; then
    crt_java_branch=$4
fi

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

if [ ! -e /tmp/aws-crt-${variant}-${arch}.tar.gz ]; then
    aws s3 cp s3://aws-crt-builder/_docker/aws-crt-${variant}-${arch}.tar.gz /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}.tar.gz
fi

container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint /bin/sh docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version})
docker exec ${container} sh -c "cd /tmp && builder build -p aws-crt-java --branch=${crt_java_branch} || true"
docker exec ${container} sh -c "tar cvzf /tmp/maven-${variant}-${arch}.tar.gz -C /root/.m2 ."
docker exec ${container} sh -c "aws s3 cp /tmp/maven-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/maven/maven-${variant}-${arch}.tar.gz"
docker stop ${container}
