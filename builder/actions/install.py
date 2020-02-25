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

import argparse

from action import Action
from host import current_platform, package_tool
from actions.script import Script
from toolchain import Toolchain


class InstallPackages(Action):
    """ Installs prerequisites to building. If packages are specified, only those packages will be installed. Otherwise, config packages will be installed. """

    pkg_init_done = False

    def __init__(self, packages=[]):
        self.packages = packages

    def run(self, env):
        config = env.config
        packages = self.packages if self.packages else config.get(
            'packages', [])
        if not packages:
            return

        pkg_tool = package_tool()
        print('Installing packages via {}: {}'.format(
            pkg_tool.value, ', '.join(packages)))

        sh = env.shell
        sudo = config.get('sudo', current_platform() == 'linux')
        sudo = ['sudo'] if sudo else []

        parser = argparse.ArgumentParser()
        parser.add_argument('--skip-install', action='store_true')
        args = parser.parse_known_args(env.args.args)[0]

        was_dryrun = sh.dryrun
        if args.skip_install:
            sh.dryrun = True

        if not InstallPackages.pkg_init_done:
            pkg_setup = config.get('pkg_setup', [])
            if pkg_setup:
                for cmd in pkg_setup:
                    if isinstance(cmd, str):
                        cmd = cmd.split(' ')
                    assert isinstance(cmd, list)
                    sh.exec(*sudo, cmd, check=True, retries=3)

            pkg_update = config.get('pkg_update', None)
            if pkg_update:
                pkg_update = pkg_update.split(' ')
                sh.exec(*sudo, pkg_update, check=True, retries=3)

            InstallPackages.pkg_init_done = True

        pkg_install = config['pkg_install']
        if not isinstance(pkg_install, list):
            pkg_install = pkg_install.split(' ')
        pkg_install += packages

        sh.exec(*sudo, pkg_install, check=True, retries=3)

        if args.skip_install:
            sh.dryrun = was_dryrun


class InstallCompiler(Action):
    def run(self, env):
        config = env.config
        if not config.get('needs_compiler'):
            print('Compiler is not required for current configuration, skipping.')
            return

        # verify compiler
        compiler = env.build_spec.compiler
        version = env.build_spec.compiler_version
        if version == 'default':
            version = None

        # See if the compiler is already installed
        compiler_path, found_version = Toolchain.find_compiler(
            env, compiler, version)
        if compiler_path:
            print('Compiler {} {} is already installed ({})'.format(
                compiler, version, compiler_path))
            return

        def _export_compiler(_env):
            if current_platform() == 'windows':
                return

            if compiler != 'default':
                for cvar, evar in {'c': 'CC', 'cxx': 'CXX'}.items():
                    exe = config.get(cvar)
                    if exe:
                        compiler_path = env.shell.where(exe)
                        if compiler_path:
                            env.shell.setenv(evar, compiler_path)
                        else:
                            print(
                                'WARNING: Compiler {} could not be found'.format(exe))

        packages = config['compiler_packages']
        return Script([InstallPackages(packages), _export_compiler])
