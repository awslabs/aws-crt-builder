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
import os
import sys

# If this is running locally for debugging, we need to add the current directory, when packaged this is a non-issue
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # nopep8

from spec import BuildSpec
from actions.script import Script
from actions.install import InstallTools
from actions.git import DownloadDependencies
from actions.cmake import CMakeBuild, CTestRun
from env import Env
from scripts import Scripts
from config import produce_config, validate_build
from toolchain import Toolchain
from host import current_platform, current_host, current_arch

import api  # force API to load and expose the virtual module


########################################################################################################################
# RUN BUILD
########################################################################################################################

def run_action(action, env):

    # Set build environment from config
    env.shell.pushenv()
    for var, value in config.get('build_env', {}).items():
        env.shell.setenv(var, value)

    if isinstance(action, str):
        action_cls = Scripts.find_action(action)
        action = action_cls()

    Scripts.run_action(
        Script([
            InstallTools(),
            DownloadDependencies(),
            action,
        ], name='run_build'),
        env
    )

    env.shell.popenv()


def run_build(build_spec, env):

    build_action = CMakeBuild()
    test_action = CTestRun()

    prebuild_action = Script(config.get(
        'pre_build_steps', []), name='pre_build_steps')
    postbuild_action = Script(config.get(
        'post_build_steps', []), name='post_build_steps')

    build_steps = config.get('build_steps', config.get('build', None))
    if build_steps:
        build_action = Script(build_steps, name='build')

    test_steps = config.get('test_steps', config.get('test', None))
    if test_steps:
        test_action = Script(test_steps, name='test')

    build = Script([
        prebuild_action,
        build_action,
        postbuild_action,
        test_action,
    ], name='run_build')
    run_action(build, env)


def default_spec(env):
    target = current_platform()
    host = current_host()
    arch = current_arch()
    compiler, version = Toolchain.default_compiler(env)
    print('Using Default Spec:')
    print('  Host: {} {}'.format(host, arch))
    print('  Target: {} {}'.format(target, arch))
    print('  Compiler: {} {}'.format(compiler, version))
    return BuildSpec(host=host, compiler=compiler, compiler_version='{}'.format(version), target=target, arch=arch)


def inspect_host(env):
    spec = env.build_spec
    toolchain = Toolchain(env, spec=spec)
    print('Host Environment:')
    print('  Host: {} {}'.format(spec.host, spec.arch))
    print('  Default Target: {} {}'.format(spec.target, spec.arch))
    print('  Default Compiler: {} (version: {}) {}'.format(
        spec.compiler, toolchain.compiler_version, toolchain.compiler_path(env)))
    compilers = ['{} {}'.format(c[0], c[1])
                 for c in Toolchain.all_compilers(env)]
    print('  Available Compilers: {}'.format(', '.join(compilers)))
    print('  Available Projects: {}'.format(', '.join(env.projects())))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help="Don't run the build, just print the commands that would run")
    parser.add_argument('-p', '--project', action='store',
                        type=str, help="Project to work on")
    parser.add_argument('--config', type=str, default='RelWithDebInfo',
                        help='The native code configuration to build with')
    parser.add_argument('--dump-config', action='store_true',
                        help="Print the config in use before running a build")
    parser.add_argument('--spec', type=str, dest='build')
    parser.add_argument('-b', '--build-dir', type=str,
                        help='Directory to work in', default='build')
    commands = parser.add_subparsers(dest='command')

    build = commands.add_parser(
        'build', help="Run target build, formatted 'host-compiler-compilerversion-target-arch'. Ex: linux-ndk-19-android-arm64v8a")
    build.add_argument('build', type=str, default='default', nargs='?')
    build.add_argument('args', nargs=argparse.REMAINDER)

    run = commands.add_parser('run', help='Run action. Ex: do-thing')
    run.add_argument('run', type=str)
    run.add_argument('args', nargs=argparse.REMAINDER)

    inspect = commands.add_parser(
        'inspect', help='Dump information about the current host')

    args = parser.parse_args()

    # set up environment
    env = Env({
        'dryrun': args.dry_run,
        'args': args,
        'project': args.project,
    })

    build_name = getattr(args, 'build', None)
    if build_name:
        build_spec = env.build_spec = BuildSpec(spec=build_name)
    else:
        build_spec = env.build_spec = default_spec(env)

    inspect_host(env)
    if args.command == 'inspect':
        sys.exit(0)

    if not env.project:
        print('No project specified and no project found in current directory')
        sys.exit(1)

    # Build the config object
    config_file = os.path.join(env.project.path, "builder.json")
    config = env.config = produce_config(
        build_spec, config_file,
        source_dir=env.source_dir,
        build_dir=env.build_dir,
        install_dir=env.install_dir,
        project=env.project.name,
        project_dir=env.project.path,
        spec=str(build_spec))
    if not env.config.get('enabled', True):
        raise Exception("The project is disabled in this configuration")

    if getattr(args, 'dump_config', False):
        from pprint import pprint
        pprint(build_spec)
        pprint(config)

    validate_build(build_spec)

    # Once initialized, switch to the source dir before running actions
    env.shell.rm(env.build_dir)
    env.shell.mkdir(env.build_dir)
    env.shell.cd(env.project.path)

    # Run a build with a specific spec/toolchain
    if args.command == 'build':
        print("Running build", build_spec.name, flush=True)
        run_build(build_spec, env)

    # run a single action, usually local to a project
    elif args.command == 'run':
        action = args.run
        run_action(action, env)
