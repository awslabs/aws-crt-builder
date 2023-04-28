# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from setuptools import setup, find_packages
from subprocess import check_output
import re

git_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
version = 'v0.1+{}'.format(git_branch)
if git_branch in ['master', 'main']:
    git_rev = check_output(['git', 'describe', '--abbrev=0'], text=True).strip()
    version = git_rev

setup(
    name="builder",
    version=version,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'builder = builder.main:main'
        ]
    },
    author='AWS SDK Common Runtime Team',
    author_email='aws-sdk-common-runtime@amazon.com',
    project_urls={
        "Source": "https://github.com/awslabs/aws-crt-builder"
    }
)