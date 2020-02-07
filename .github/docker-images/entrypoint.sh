#!/bin/sh

set -ex

builder=/usr/local/bin/builder

cd $GITHUB_WORKSPACE
$builder $*
