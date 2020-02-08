# Copyright 2010-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#  http://aws.amazon.com/apache2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

from setuptools import setup, find_packages
from subprocess import check_output

git_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
version = 'v0.1-{}'.format(git_branch)
if git_branch == 'master':
    git_rev = check_output(['git', 'describe', '--abbrev=0'])
    version = git_rev

setup(
    name="builder",
    version=version,
    packages=find_packages(),
    scripts=['builder/*.py'],
    author='AWS SDK Common Runtime Team',
    author_email='aws-sdk-common-runtime@amazon.com',
    project_urls={
        "Source": "https://github.com/awslabs/aws-crt-builder"
    }
)
