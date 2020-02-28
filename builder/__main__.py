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

from __future__ import print_function
import argparse
import os
import re
import sys

# If this is running locally for debugging, we need to add the current directory, when packaged this is a non-issue
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # nopep8

from spec import BuildSpec
from actions.script import Script
from actions.install import InstallPackages, InstallCompiler
from actions.git import DownloadDependencies
from env import Env
from project import Project
from scripts import Scripts
from toolchain import Toolchain
from host import current_os, current_host, current_arch, current_platform
import data

import api  # force API to load and expose the virtual module
import imports  # load up all known import classes


########################################################################################################################
# RUN BUILD
########################################################################################################################

def run_action(action, env):
    config = env.config
    # Set build environment from config
    env.shell.pushenv()
    for var, value in config.get('build_env', {}).items():
        env.shell.setenv(var, value)
    for var, value in getattr(env, 'env', {}).items():
        env.shell.setenv(var, value)

    if isinstance(action, str):
        action_cls = Scripts.find_action(action)
        if not action_cls:
            print('Action {} not found'.format(action))
            sys.exit(13)
        action = action_cls()

    Scripts.run_action(
        Script([
            InstallCompiler(),
            InstallPackages(),
            DownloadDependencies(),
            action,
        ], name='main'),
        env
    )

    env.shell.popenv()


def run_build(env):
    config = env.config

    print("Running build", env.spec.name, flush=True)

    def pre_build(env):
        return env.project.pre_build(env)

    def build(env):
        return env.project.build(env)

    def post_build(env):
        return env.project.post_build(env)

    def test(env):
        return env.project.test(env)

    def install(env):
        return env.project.install(env)

    def build_consumers(env):
        if env.spec.downstream:
            env.project.build_consumers(env)

    build = Script([
        pre_build,
        build,
        post_build,
        test,
        install,
        build_consumers,
    ], name='run_build {}'.format(env.project.name))
    run_action(build, env)


def default_spec(env):
    target, arch = env.platform.split('-')
    host = current_host()
    compiler, version = Toolchain.default_compiler(env, target, arch)
    print('Using Spec:')
    print('  Host: {} {}'.format(host, current_arch()))
    print('  Target: {} {}'.format(target, arch))
    print('  Compiler: {} {}'.format(compiler, version))
    return BuildSpec(host=host, compiler=compiler, compiler_version='{}'.format(version), target=target, arch=arch)


def inspect_host(env):
    spec = env.spec
    toolchain = Toolchain(env, spec=spec)
    print('Host Environment:')
    print('  Host: {} {}'.format(spec.host, spec.arch))
    print('  Default Target: {} {}'.format(spec.target, spec.arch))
    compiler_path = toolchain.compiler_path(env)
    if not compiler_path:
        compiler_path = '(Will Install)'
    print('  Compiler: {} (version: {}) {}'.format(
        spec.compiler, toolchain.compiler_version, compiler_path))
    compilers = ['{} {}'.format(c[0], c[1])
                 for c in Toolchain.all_compilers(env)]
    print('  Available Compilers: {}'.format(', '.join(compilers)))
    print('  Available Projects: {}'.format(', '.join(Project.projects())))


def parse_extra_args(env):
    args = getattr(env.args, 'args', [])
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=str,
                        help="The compiler to use for this build")
    parser.add_argument(
        '--target', type=str, help="The target to cross-compile for (e.g. android, linux-x86, aarch64)")
    # parse the args we know, pass the rest on to actions to figure out
    args, env.args.args = parser.parse_known_args(args)

    if args.compiler or args.target:
        compiler, version = (None, None)
        if args.compiler:
            compiler, version = args.compiler.split('-')
        spec = str(env.spec) if hasattr(
            env, 'spec') else getattr(env.args, 'spec', None)
        env.spec = BuildSpec(compiler=compiler,
                             compiler_version=version, target=args.target, spec=spec)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help="Don't run the build, just print the commands that would run")
    parser.add_argument('-p', '--project', action='store',
                        type=str, help="Project to work on")
    parser.add_argument('--config', type=str, default='RelWithDebInfo',
                        help='The native code configuration to build with')
    parser.add_argument('--dump-config', action='store_true',
                        help="Print the config in use before running a build")
    parser.add_argument('--spec', type=str)
    parser.add_argument('-b', '--build-dir', type=str,
                        help='Directory to work in', default='.')
    parser.add_argument('--branch', help='Branch to build from')
    parser.add_argument(
        '--platform', help='Target platform to compile/cross-compile for', default='{}-{}'.format(current_os(), current_arch()),
        choices=data.PLATFORMS)
    parser.add_argument('--cli_config', action='append', type=list)
    parser.add_argument('args', nargs=argparse.REMAINDER)

    # hand parse command and spec from within the args given
    command = None
    spec = None
    argv = sys.argv[1:]

    # eat command and optionally spec
    if argv and not argv[0].startswith('-'):
        command = argv.pop(0)
        if len(argv) >= 1 and not argv[0].startswith('-'):
            spec = argv.pop(0)

    # pull out any k=v pairs
    config_vars = []
    for arg in argv:
        m = re.match(r'^([A-Za-z_0-9]+)=(.+)', arg)
        if m:
            config_vars.append((m.group(1), m.group(2)))
    cli_config = {}
    for var in config_vars:
        cli_config[var[0]] = var[1]
        argv.remove('{}={}'.format(var[0], var[1]))

    # parse the args we know, put the rest in args.args for others to parse
    args, extras = parser.parse_known_args(argv)
    args.command = command
    args.cli_config = cli_config
    if not args.spec:
        args.spec = spec
    args.args += extras
    # Backwards compat for `builder run $action`
    if args.command == 'run':
        args.command = args.spec
        args.spec = None

    return args


if __name__ == '__main__':
    args = parse_args()

    # set up environment
    env = Env({
        'dryrun': args.dry_run,
        'args': args,
        'project': args.project,
        'branch': args.branch,
        'platform': args.platform,
    })

    parse_extra_args(env)

    if not getattr(env, 'spec', None):
        build_name = getattr(args, 'spec', getattr(args, 'build', None))
        if build_name:
            env.spec = BuildSpec(spec=build_name, platform=env.platform)
        else:
            env.spec = default_spec(env)

    if env.platform == current_platform():
        inspect_host(env)
    if args.command == 'inspect':
        sys.exit(0)

    if not env.project:
        print('No project specified and no project found in current directory')
        sys.exit(1)

    # Build the config object
    env.config = env.project.get_config(
        env.spec,
        env.args.cli_config,
        source_dir=env.source_dir,
        build_dir=env.build_dir,
        install_dir=env.install_dir,
        project_dir=env.project.path)

    if not env.config.get('enabled', True):
        raise Exception("The project is disabled in this configuration")

    if env.config.get('needs_compiler', True):
        env.toolchain = Toolchain(env, spec=env.spec)

    if args.dump_config:
        from pprint import pprint
        print('Spec: ', end='')
        pprint(env.spec)
        print('Config:')
        pprint(env.config)

    # Run a build with a specific spec/toolchain
    if args.command == 'build':
        run_build(env)
    # run a single action, usually local to a project
    else:
        run_action(args.command, env)
