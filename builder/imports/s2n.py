# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.project import Project, Import


config = {
    'targets': ['linux', 'android'],
    'test_steps': [],
    'build_tests': False,
}


class S2NImport(Import):
    def __init__(self, **kwargs):
        super().__init__(
            library=True,
            imports=['libcrypto'],
            config=config,
            **kwargs)


class S2NProject(Project):
    def __init__(self, **kwargs):
        super().__init__(
            account='awslabs',
            imports=['libcrypto'],
            config=config,
            **kwargs)
