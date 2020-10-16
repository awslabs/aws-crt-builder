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
if [ -x /opt/python/cp39-cp39/bin/python ] && [ ! -e /usr/local/bin/python3 ]; then
    ln -s /opt/python/cp39-cp39/bin/python /usr/local/bin/python3
fi

# Figure out where to work based on environment, default to .
if [ -d "$GITHUB_WORKSPACE" ]; then
    cd $GITHUB_WORKSPACE
elif [ -d "$CODEBUILD_SRC_DIR" ]; then
    cd $CODEBUILD_SRC_DIR
fi

# Launch the builder with whatever args were passed to this script
$builder ${args[@]}
