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
import os
import shutil
import stat
import sys
from pathlib import Path

from action import Action
from host import current_os, package_tool
from actions.script import Script
from toolchain import Toolchain
from util import list_unique


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

        packages = list_unique(packages)
        pkg_tool = package_tool()
        print('Installing packages via {}: {}'.format(
            pkg_tool.value, ', '.join(packages)))

        sh = env.shell
        sudo = config.get('sudo', current_os() == 'linux')
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
                for cmd in list_unique(pkg_setup):
                    if isinstance(cmd, str):
                        cmd = cmd.split(' ')
                    assert isinstance(cmd, list)
                    sh.exec(*sudo, cmd, check=True, retries=3)

            pkg_update = config.get('pkg_update', None)
            if pkg_update:
                if not isinstance(pkg_update, list):
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
        sh = env.shell
        if not config.get('needs_compiler'):
            print('Compiler is not required for current configuration, skipping.')
            return

        toolchain = env.toolchain
        assert toolchain

        # Cross compile with dockcross
        def _install_cross_compile_toolchain(env):
            print(
                'Installing cross-compile via dockcross for {}'.format(toolchain.platform))
            cross_compile_platform = env.config.get(
                'cross_compile_platform', toolchain.platform)
            result = sh.exec(
                'docker', 'run', 'dockcross/{}'.format(cross_compile_platform), quiet=True)
            # Strip off any output from docker itself
            output, shebang, script = result.output.partition('#!')
            script = shebang + script
            print(output)
            assert result.returncode == 0

            dockcross = os.path.abspath(os.path.join(
                env.build_dir, 'dockcross-{}'.format(cross_compile_platform)))
            Path(dockcross).touch(0o755)
            with open(dockcross, "w+t") as f:
                f.write(script)
            sh.exec('chmod', 'a+x', dockcross)

            # Write out build_dir/dockcross.env file to init the dockcross env with
            # other code can add to this
            dockcross_env = os.path.join(env.build_dir, 'dockcross.env')
            with open(dockcross_env, "w+") as f:
                f.write('#env for dockcross\n')
            toolchain.env_file = dockcross_env
            toolchain.shell_env = [
                dockcross, '-a', '--env-file={}'.format(dockcross_env)]

        # Expose compiler via environment
        def export_compiler(_env):
            if current_os() == 'windows':
                return

            if compiler != 'default':
                for cvar, evar in {'c': 'CC', 'cxx': 'CXX'}.items():
                    exe = config.get(cvar)
                    if exe:
                        compiler_path = env.shell.where(
                            exe, resolve_symlinks=False)
                        if compiler_path:
                            env.shell.setenv(evar, compiler_path)
                        else:
                            print(
                                'WARNING: Compiler {} could not be found'.format(exe))

        if not toolchain.cross_compile:
            # Compiler is local, or should be, so verify/install and export it
            compiler = env.spec.compiler
            version = env.spec.compiler_version
            if version == 'default':
                version = None

            # See if the compiler is already installed
            compiler_path, found_version = Toolchain.find_compiler(
                compiler, version)
            if compiler_path:
                print('Compiler {} {} is already installed ({})'.format(
                    compiler, version, compiler_path))
                return Script([export_compiler])

        packages = list_unique(config.get('compiler_packages', []))
        after_packages = [export_compiler]
        if toolchain.cross_compile:
            after_packages = [_install_cross_compile_toolchain]
        return Script([InstallPackages(packages), *after_packages])
