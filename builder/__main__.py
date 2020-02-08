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
if __name__ == '__main__':  # nopep8
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # nopep8

from spec import BuildSpec
from actions.script import Script
from actions.install import InstallTools
from actions.git import DownloadDependencies
from actions.cmake import CMakeBuild, CTestRun
from env import Env
from build import Builder
from config import produce_config


########################################################################################################################
# RUN BUILD
########################################################################################################################
def run_build(build_spec, env):

    build_action = CMakeBuild()
    test_action = CTestRun()

    prebuild_action = Script(config.get(
        'pre_build_steps', []), name='pre_build_steps')
    postbuild_action = Script(config.get(
        'post_build_steps', []), name='post_build_steps')

    build_steps = config.get('build', None)
    if build_steps:
        build_action = Script(build_steps, name='build')

    test_steps = config.get('test', None)
    if test_steps:
        test_action = Script(test_steps, name='test')

    # Set build environment
    env.shell.pushenv()
    for var, value in config.get('build_env', {}).items():
        env.shell.setenv(var, value)

    Builder.run_action(
        Script([
            InstallTools(),
            DownloadDependencies(),
            prebuild_action,
            build_action,
            postbuild_action,
            test_action,
        ], name='run_build'),
        env
    )

    env.shell.popenv()

########################################################################################################################
# MAIN
########################################################################################################################


def default_spec(env):

    compiler = 'gcc'
    version = 'default'
    target = host = 'default'

    arch = ('x64' if sys.maxsize > 2**32 else 'x86')

    if sys.platform in ('linux', 'linux2'):
        target = host = 'linux'
        clang_path, clang_version = env.find_llvm_tool('clang')
        gcc_path, gcc_version = env.find_gcc_tool('gcc')
        if clang_path:
            print('Found clang {} as default compiler'.format(clang_version))
            compiler = 'clang'
            version = clang_version
        elif gcc_path:
            print('Found gcc {} as default compiler'.format(gcc_version))
            compiler = 'gcc'
            version = gcc_version
        else:
            print(
                'Neither GCC or Clang could be found on this system, perhaps not installed yet?')

        if os.uname()[4][:3].startswith('arm'):
            arch = ('armv8' if sys.maxsize > 2**32 else 'armv7')

    elif sys.platform in ('win32'):
        target = host = 'windows'
        compiler = 'msvc'
    elif sys.platform in ('darwin'):
        target = host = 'macos'
        compiler = 'clang'

    return BuildSpec(host=host, compiler=compiler, compiler_version='{}'.format(version), target=target, arch=arch)


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
    build.add_argument('build', type=str, default='default')
    build.add_argument('--skip-install', action='store_true',
                       help="Skip the install phase, useful when testing locally")

    run = commands.add_parser('run', help='Run action. Ex: do-thing')
    run.add_argument('run', type=str)
    run.add_argument('args', nargs=argparse.REMAINDER)

    codebuild = commands.add_parser('codebuild', help="Create codebuild jobs")
    codebuild.add_argument(
        'project', type=str, help='The name of the repo to create the projects for')
    codebuild.add_argument('--github-account', type=str, dest='github_account',
                           default='awslabs', help='The GitHub account that owns the repo')
    codebuild.add_argument('--profile', type=str, default='default',
                           help='The profile in ~/.aws/credentials to use when creating the jobs')
    codebuild.add_argument('--inplace-script', action='store_true',
                           help='Use the python script in codebuild/builder.py instead of downloading it')
    codebuild.add_argument(
        '--config', type=str, help='The config file to use when generating the projects')

    args = parser.parse_args()

    # set up builder and environment
    builder = Builder()
    env = Env({
        'dryrun': args.dry_run,
        'args': args,
        'project': args.project,
    })

    # Build the config object
    config_file = os.path.join(env.project.path, "builder.json")
    build_name = getattr(args, 'build', None)
    if build_name:
        build_spec = env.build_spec = BuildSpec(spec=build_name)
    else:
        build_spec = env.build_spec = default_spec(env)
    config = env.config = produce_config(build_spec, config_file)
    if not env.config['enabled']:
        raise Exception("The project is disabled in this configuration")

    if getattr(args, 'dump_config', False):
        from pprint import pprint
        pprint(config)

    # Run a build with a specific spec/toolchain
    if args.command == 'build':
        print("Running build", build_spec.name, flush=True)
        run_build(build_spec, env)

    # run a single action, usually local to a project
    elif args.command == 'run':
        action = args.run
        builder.run_action(action, env)
