# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.project import Project, Import


config = {
    'targets': ['linux', 'android'],
    'test_steps': [],
    'build_tests': False,
    # s2n contains pq crypto code where there is a mismatch (bounded array vs. pointer) in function
    # signatures between the declaration and implementation, leading to mismatched bound warnings that
    # turn into errors.  While s2n should fix these as they come in, their existence shouldn't break our builds.
    'cmake_args': ['-DUNSAFE_TREAT_WARNINGS_AS_ERRORS=OFF']
}


class S2NImport(Import):
    def __init__(self, **kwargs):
        super().__init__(
            library=True,
            imports=['aws-lc'],
            config=config,
            url='https://github.com/aws/s2n-tls.git',
            **kwargs)


class S2NProject(Project):
    def __init__(self, **kwargs):
        super().__init__(
            account='awslabs',
            imports=['aws-lc'],
            url='https://github.com/aws/s2n-tls.git',
            **config,
            **kwargs)
