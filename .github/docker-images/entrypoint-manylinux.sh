#!/bin/sh

set -ex

BUILDER_ARGS=$BUILDER_ARGS $*

python=/opt/python/cp37-cp37m/bin/python
builder=/usr/local/bin/builder

cd $GITHUB_WORKSPACE
$python $builder $BUILDER_ARGS
