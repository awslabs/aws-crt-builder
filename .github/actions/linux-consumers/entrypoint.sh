#!/bin/sh

set -ex

package=$1
spec=$2

cd $GITHUB_WORKSPACE
python3 -c "from urllib.request import urlretrieve; urlretrieve('https://raw.githubusercontent.com/awslabs/aws-c-common/master/codebuild/builder.py', 'builder.py')"
python3 -m virtualenv venv
python="`pwd`/venv/bin/python"
builder="$python `pwd`/builder.py"
git clone https://github.com/awslabs/$package.git
cd $package
$builder builder.py build ${spec}-downstream

