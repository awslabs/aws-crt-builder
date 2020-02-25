#!/bin/sh

set -ex

builder=/usr/local/bin/builder.pyz
chmod a+x $builder
# on manylinux, use the latest python3
if [ -x /opt/python/cp37-cp37m/bin/python ]; then
    ln -s /opt/python/cp37-cp37m/bin/python /usr/local/bin/python3
fi

cd $GITHUB_WORKSPACE
$builder $*
