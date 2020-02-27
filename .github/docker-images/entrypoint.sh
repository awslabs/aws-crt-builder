#!/usr/bin/env bash

set -ex

args=($*)

version=LATEST
if [ "${args[0]}" == "--version=*" ]; then
    version=${args[@]:1}
    version=$(echo $version | cut -f2 -d=)
fi

# download the version of builder requested
curl -sSL -o /usr/local/bin/builder.pyz --retry 3 --retry-delay 3 --retry-max-time 30 https://d19elf31gohf1l.cloudfront.net/${version}/builder
builder=/usr/local/bin/builder.pyz
chmod a+x $builder

# on manylinux, use the latest python3 via symlink
if [ -x /opt/python/cp37-cp37m/bin/python ]; then
    ln -s /opt/python/cp37-cp37m/bin/python /usr/local/bin/python3
fi

cd $GITHUB_WORKSPACE
$builder $*
