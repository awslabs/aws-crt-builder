# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from host import current_os
from actions.install import InstallPackages
from project import Import
from actions.script import Script
from toolchain import Toolchain
from util import UniqueList


class GCC(Import):
    def __init__(self, **kwargs):
        super().__init__(
            compiler=True,
            config={
                'targets': ['linux'],
            },
            **kwargs)
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        config = env.config

        # Ensure additional compiler packages are installed
        packages = UniqueList(config.get('compiler_packages', []))
        packages = [p for p in packages if not p.startswith('gcc')]
        Script([InstallPackages(packages)],
               name='Install compiler prereqs').run(env)

        installed_path, installed_version = Toolchain.find_compiler(
            env.spec.compiler, env.spec.compiler_version)
        if installed_path:
            print('Compiler {} {} already exists at {}'.format(
                env.spec.compiler, installed_version, installed_path))
            self.installed = True
            return

        # It's ok to attempt to install packages redundantly, they won't hurt anything
        packages = UniqueList(config.get('compiler_packages', []))

        Script([InstallPackages(packages)], name='install gcc').run(env)

        self.installed = True
