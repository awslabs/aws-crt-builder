# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.project import Project, Import


config = {
    'targets': ['macos', 'linux', 'android'],
    'test_steps': [],
    'build_tests': False,
    'cmake_args': ['-fPIC']
}


class BoringSSLImport(Import):
    def __init__(self, **kwargs):
        super().__init__(
            library=True,
            name='boringssl',
            config=config,
            **kwargs)

    def cmake_args(self, env):
        assert self.installed
        return super().cmake_args(env) + [
            "-DLibCrypto_INCLUDE_DIR={}/include".format(self.prefix),
            "-DLibCrypto_STATIC_LIBRARY={}/lib/libcrypto.a".format(
                self.prefix),
        ]


class BoringSSLProject(Project):
    def __init__(self, **kwargs):
        super().__init__(
            account='google',
            url='https://github.com/google/boringssl.git',
            revision='9939e14cffc66f9b9f3374fb52c97bd8bfb0bfbe',
            **config,
            **kwargs)
