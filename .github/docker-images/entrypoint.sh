#!/bin/sh

set -ex

builder=/usr/local/bin/builder

chmod a+x $builder
cd $GITHUB_WORKSPACE
$builder $*
