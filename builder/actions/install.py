# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path
from functools import partial

from action import Action
from host import current_os, package_tool
from actions.script import Script
from toolchain import Toolchain
from util import UniqueList


def set_dryrun(dryrun, env):
    env.shell.dryrun = dryrun


class InstallPackages(Action):
    """ Installs prerequisites to building. If packages are specified, only those packages will be installed. Otherwise, config packages will be installed. """

    pkg_init_done = False

    def __init__(self, packages=[]):
        self.packages = packages

    def run(self, env):
        config = env.config
        sh = env.shell

        parser = argparse.ArgumentParser()
        parser.add_argument('--skip-install', action='store_true')
        args = parser.parse_known_args(env.args.args)[0]

        sudo = config.get('sudo', current_os() == 'linux')
        sudo = ['sudo'] if sudo else []

        packages = self.packages if self.packages else config.get(
            'packages', [])
        if packages:
            packages = UniqueList(packages)
            pkg_tool = package_tool()
            print('Installing packages via {}: {}'.format(
                pkg_tool.value, ', '.join(packages)))

            was_dryrun = sh.dryrun
            if args.skip_install:
                sh.dryrun = True

            if not InstallPackages.pkg_init_done:
                pkg_setup = UniqueList(config.get('pkg_setup', []))
                if pkg_setup:
                    for cmd in pkg_setup:
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

        setup_steps = env.config.get('setup_steps', [])
        if setup_steps:
            steps = []
            for step in setup_steps:
                if not isinstance(step, list):
                    step = step.split(' ')
                if step:
                    steps.append([*sudo, *step])
            if args.skip_install:
                return Script([partial(set_dryrun, True), *steps,
                               partial(set_dryrun, sh.dryrun)], name='setup')

            return Script(steps, name='setup')


# Expose compiler via environment
def export_compiler(compiler, env):
    if current_os() == 'windows':
        return

    if compiler != 'default':
        for cvar, evar in {'c': 'CC', 'cxx': 'CXX'}.items():
            exe = env.config.get(cvar)
            if exe:
                compiler_path = env.shell.where(exe, resolve_symlinks=False)
                if compiler_path:
                    env.shell.setenv(evar, compiler_path)
                else:
                    print(
                        'WARNING: Compiler {} could not be found'.format(exe))


class InstallCompiler(Action):
    def run(self, env):
        config = env.config
        sh = env.shell
        if not config.get('needs_compiler'):
            print('Compiler is not required for current configuration, skipping.')
            return

        assert env.toolchain
        toolchain = env.toolchain

        # add dockcross as an implicit import if cross-compiling
        if toolchain.cross_compile:
            setattr(env.project, 'imports', getattr(
                env.project, 'imports', []) + ['dockcross'])

        imports = env.project.get_imports(env.spec)
        for imp in imports:
            if imp.compiler:
                imp.install(env)

        export_compiler(env.spec.compiler, env)
