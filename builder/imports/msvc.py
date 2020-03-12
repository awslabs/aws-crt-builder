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
from project import Import
from toolchain import Toolchain


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

        sh = env.shell
        toolchain = env.toolchain

        installed_path, installed_version = Toolchain.find_compiler(
            env.spec.compiler, env.spec.compiler_version)
        if installed_path:
            print('Compiler {} {} already exists at {}'.format(
                env.spec.compiler, installed_version, installed_path))
            self.installed = True
            return

        raise Exception('MSVC does not support dynamic install, and {} {} could not be found'.format(
            env.spec.compiler, env.spec.compiler_version))
