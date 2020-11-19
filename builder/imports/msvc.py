# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from core.host import current_os
from core.project import Import
from core.toolchain import Toolchain
from core.util import UniqueList
from actions.install import InstallPackages
from actions.script import Script


class MSVC(Import):
    def __init__(self, **kwargs):
        super().__init__(
            compiler=True,
            config={
                'targets': ['windows'],
            },
            **kwargs)
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        config = env.config

        # Ensure compiler packages are installed
        packages = UniqueList(config.get('compiler_packages', []))
        Script([InstallPackages(packages)],
               name='Install compiler prereqs').run(env)

        installed_path, installed_version = Toolchain.find_compiler(
            env.spec.compiler, env.spec.compiler_version)
        if installed_path:
            print('Compiler {} {} already exists at {}'.format(
                env.spec.compiler, installed_version, installed_path))
            self.installed = True
            return

        raise EnvironmentError('MSVC does not support dynamic install, and {} {} could not be found'.format(
            env.spec.compiler, env.spec.compiler_version))
