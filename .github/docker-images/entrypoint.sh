#!/usr/bin/env bash

set -ex

args=("$@")

version=LATEST
if [[ "${args[0]}" == "--version="* ]]; then
    version=${args[0]}
    version=$(echo $version | cut -f2 -d=)
    args=${args[@]:1}
fi

if [ $(echo $version | grep -E '^v[0-9\.]+$') ]; then
    version=releases/$version
elif [[ $version != 'channels/'* ]]; then
    version=channels/$version
fi

# download the version of builder requested
curl -sSL -o /usr/local/bin/builder.pyz --retry 3 https://d19elf31gohf1l.cloudfront.net/${version}/builder.pyz?date=`date +%s`
builder=/usr/local/bin/builder.pyz
chmod a+x $builder

# on manylinux, use the latest python3 via symlink
if [ -x /opt/python/cp37-cp37m/bin/python ]; then
    ln -s /opt/python/cp37-cp37m/bin/python /usr/local/bin/python3
fi

cd $GITHUB_WORKSPACE
$builder ${args[@]}
