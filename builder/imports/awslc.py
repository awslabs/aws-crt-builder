# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os

from builder.core.project import Project, Import
from builder.actions.git import DownloadSource


config = {
    'targets': ['linux', 'android'],
    'test_steps': [],
    'build_tests': False,
    'cmake_args': ['-DDISABLE_GO=ON', '-DBUILD_LIBSSL=OFF', '-DDISABLE_PERL=ON']
}


class AWSLCImport(Import):
    def __init__(self, **kwargs):
        if kwargs.get('name'):
            del kwargs['name']
        super().__init__(
            library=True,
            account='aws',
            name='aws-lc',
            config=config,
            **kwargs)

    def pre_build(self, env):
        # Search for an aws-lc directory
        if not hasattr(self, 'path'):
            for root, dirs, files in os.walk(env.deps_dir):
                for search_dir in dirs:
                    if search_dir.endswith('aws-lc'):
                        self.path = os.path.join(root, search_dir)
                        break
        # No aws-lc directory, download to deps dir now
        if not hasattr(self, 'path'):
            self.path = os.path.join(env.deps_dir, 'aws-lc')
            DownloadSource(project=Project.find_project(self.name), path=env.deps_dir).run(env)

    def build(self, env):
        return Project.build(Project.find_project(self.name, [self.path]), env)


class AWSLCProject(Project):
    def __init__(self, **kwargs):
        if kwargs.get('name'):
            del kwargs['name']
        super().__init__(
            account='aws',
            name='aws-lc',
            **config,
            **kwargs)

    def cmake_args(self, env):
        if env.spec.compiler == 'gcc' and env.spec.compiler_version.startswith('4.'):
            # Disable AVX512 on old GCC versions for aws-lc as they dont support AVX512 instructions used by aws-lc
            return super().cmake_args(env) + ['-DMY_ASSEMBLER_IS_TOO_OLD_FOR_512AVX=ON']

        return super().cmake_args(env)
