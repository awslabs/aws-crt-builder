# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.project import Project, Import


config = {
    'targets': ['linux', 'android'],
    'test_steps': [],
    'build_tests': False,
}


class AWSLCImport(Import):
    def __init__(self, **kwargs):
        super().__init__(
            library=True,
            config=config,
            **kwargs)


class AWSLCProject(Project):
    def __init__(self, **kwargs):
        super().__init__(
            account='awslabs',
            config=config,
            **kwargs)
