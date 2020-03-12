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

        sh = env.shell
        config = env.config

        installed_path, installed_version = Toolchain.find_compiler(
            env.spec.compiler, env.spec.compiler_version)
        if installed_path:
            print('Compiler {} {} already exists at {}'.format(
                env.spec.compiler, installed_version, installed_path))
            self.installed = True
            return

        sudo = env.config.get('sudo', current_os() == 'linux')
        sudo = ['sudo'] if sudo else []

        packages = UniqueList(config.get('compiler_packages', []))
        compiler = env.spec.compiler
        version = env.spec.compiler_version

        Script([InstallPackages(packages)], name='install gcc').run(env)

        self.installed = True
