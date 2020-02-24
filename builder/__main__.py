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
from actions.install import InstallPackages, InstallCompiler
from actions.git import DownloadDependencies
from actions.cmake import CMakeBuild, CTestRun
from env import Env
from project import Project
from scripts import Scripts
from toolchain import Toolchain
from host import current_platform, current_host, current_arch

import api  # force API to load and expose the virtual module


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
        ], name='run_build'),
        env
    )

    env.shell.popenv()


def run_build(env):
    config = env.config

    print("Running build", env.build_spec.name, flush=True)
    build_action = CMakeBuild()
    test_action = CTestRun()

    prebuild_action = Script(config.get(
        'pre_build_steps', []), name='pre_build_steps')
    postbuild_action = Script(config.get(
        'post_build_steps', []), name='post_build_steps')

    build_steps = config.get('build_steps', config.get('build', None))
    if build_steps:
        build_action = Script(build_steps, name='build_steps')

    test_steps = config.get('test_steps', config.get('test', None))
    if test_steps:
        test_action = Script(test_steps, name='test_steps')

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
        spec = str(env.build_spec) if hasattr(
            env, 'build_spec') else getattr(env.args, 'spec', None)
        env.build_spec = BuildSpec(compiler=compiler,
                                   compiler_version=version, target=args.target, spec=spec)


def parse_args():
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
    parser.add_argument('--spec', type=str)
    parser.add_argument('-b', '--build-dir', type=str,
                        help='Directory to work in', default='.')
    parser.add_argument('args', nargs=argparse.REMAINDER)

    # hand parse command and spec from within the args given
    command = None
    spec = None
    argv = sys.argv[1:]
    if argv and not argv[0].startswith('-'):
        command = argv.pop(0)
        if len(argv) >= 1 and not argv[0].startswith('-'):
            spec = argv.pop(0)

    # parse the args we know, put the rest in args.args for others to parse
    args, extras = parser.parse_known_args(argv)
    args.command = command
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
    })

    parse_extra_args(env)

    if not getattr(env, 'build_spec', None):
        build_name = getattr(args, 'spec', getattr(args, 'build', None))
        if build_name:
            env.build_spec = BuildSpec(spec=build_name)
        else:
            env.build_spec = default_spec(env)

    inspect_host(env)
    if args.command == 'inspect':
        sys.exit(0)

    if not env.project:
        print('No project specified and no project found in current directory')
        sys.exit(1)

    # Build the config object
    env.config = env.project.get_config(
        env.build_spec,
        source_dir=env.source_dir,
        build_dir=env.build_dir,
        install_dir=env.install_dir,
        project_dir=env.project.path)

    if not env.config.get('enabled', True):
        raise Exception("The project is disabled in this configuration")

    if getattr(args, 'dump_config', False):
        from pprint import pprint
        print('Spec: ', end='')
        pprint(env.build_spec)
        print('Config:')
        pprint(env.config)

    # Run a build with a specific spec/toolchain
    if args.command == 'build':
        run_build(env)
    # run a single action, usually local to a project
    else:
        run_action(args.command, env)
