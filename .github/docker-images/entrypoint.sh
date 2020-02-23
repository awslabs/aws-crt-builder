#!/bin/sh

set -ex

builder=/usr/local/bin/builder
chmod a+x $builder
# on manylinux, use the latest python3
if [ -x /opt/python/cp37-cp37m/bin/python ]; then
    builder=/opt/python/cp37-cp37m/bin/python $builder
fi

cd $GITHUB_WORKSPACE
$builder $*
