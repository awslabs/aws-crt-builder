#!/usr/bin/env bash

# This installs maven in the specified container, and forces it to download enough to to go offline, then caches the result

set -ex

[ $# -eq 3 ]
variant=$1
arch=$2
version=$3

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

if [ ! -e /tmp/aws-crt-${variant}-${arch}-${version}.tar.gz ]; then
    aws s3 cp s3://aws-crt-builder/_docker/aws-crt-${variant}-${arch}-${version}.tar.gz /tmp
    docker load < /tmp/aws-crt-${variant}-${arch}-${version}.tar.gz
fi

container=$(docker run -dit --env AWS_ACCESS_KEY_ID --env AWS_SECRET_ACCESS_KEY --entrypoint /bin/sh docker.pkg.github.com/awslabs/aws-crt-builder/aws-crt-${variant}-${arch}:${version})
docker exec ${container} sh -c "cd /tmp && curl -LO https://raw.githubusercontent.com/awslabs/aws-crt-java/master/pom.xml"
docker exec ${container} sh -c "cd /tmp && mvn dependency:go-offline -B --fail-never"
docker exec ${container} sh -c "tar cvzf /tmp/maven-${variant}-${arch}.tar.gz -C /root/.m2"
docker exec ${container} sh -c "aws s3 cp /tmp/maven-${variant}-${arch}.tar.gz s3://aws-crt-builder/_binaries/maven/maven-${variant}-${arch}.tar.gz"
docker stop ${container}
