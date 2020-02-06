#!/bin/sh

set -ex

builder=/usr/local/bin/builder
BUILDER_ARGS=$BUILDER_ARGS $*

cd $GITHUB_WORKSPACE
$builder $BUILDER_ARGS
