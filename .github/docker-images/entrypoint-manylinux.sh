#!/bin/sh

set -ex

python=/opt/python/cp37-cp37m/bin/python
builder=/usr/local/bin/builder

chmod a+x $builder
cd $GITHUB_WORKSPACE
$python $builder $*
