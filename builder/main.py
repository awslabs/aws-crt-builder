# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.
import argparse
import os
import re
import sys

from builder.core.spec import BuildSpec
# load up all subclasses of Action such that Scripts.load() finds them
from builder.actions.script import Script
from builder.actions.install import InstallPackages, InstallCompiler
from builder.actions.git import DownloadDependencies
from builder.actions.mirror import Mirror
from builder.actions.release import ReleaseNotes
from builder.core.env import Env
from builder.core.project import Project
from builder.core.scripts import Scripts
from builder.core.toolchain import Toolchain
from builder.core.host import current_os, current_host, current_arch, current_platform, normalize_target
from builder.core.util import UniqueList
import builder.core.data as data

import builder.core.api  # force API to load and expose the virtual module
import builder.imports  # load up all known import classes


########################################################################################################################
# RUN BUILD
########################################################################################################################

def run_action(action, env):
    config = env.config
    # Set build environment from config
    env.shell.pushenv()
    for var, value in getattr(env, 'env', {}).items():
        env.shell.setenv(var, value)

    if isinstance(action, str):
        action_cls = Scripts.find_action(action)
        if not action_cls:
            print('Action {} not found'.format(action))
            sys.exit(13)
        action = action_cls()

    if action.is_main():
        Scripts.run_action(action, env)
    else:
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
            return env.project.build_consumers(env)

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
    target, arch = current_platform().split('-')
    host = current_host()
    compiler, version = Toolchain.default_compiler(target, arch)
    return BuildSpec(host=host, compiler=compiler, compiler_version='{}'.format(version), target=target, arch=arch)


def inspect_host(spec):
    toolchain = Toolchain(spec=spec)
    print('Host Environment:')
    print('  Host: {} {}'.format(spec.host, spec.arch))
    print('  Target: {} {}'.format(spec.target, spec.arch))
    compiler_path = toolchain.compiler_path()
    if not compiler_path:
        compiler_path = '(Will Install)'
    print('  Compiler: {} (version: {}) {}'.format(
        spec.compiler, toolchain.compiler_version, compiler_path))
    compilers = ['{} {}'.format(c[0], c[1])
                 for c in Toolchain.all_compilers()]
    print('  Available Compilers: {}'.format(', '.join(compilers)))
    print('  Available Projects: {}'.format(', '.join(Project.projects())))


def coerce_arg(arg):
    if arg.lower() in ['on', 'true', 'yes']:
        return True
    if arg.lower() in ['off', 'false', 'no']:
        return False
    return arg


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
    parser.add_argument('--build-dir', type=str,
                        help='Directory to work in', default='.')
    parser.add_argument('-b', '--branch', help='Branch to build from')
    parser.add_argument('--compiler', type=str,
                        help="The compiler to use for this build")
    parser.add_argument('--target', type=str, help="The target to cross-compile for (e.g. android-armv7, linux-x86, linux-aarch64)",
                        default='{}-{}'.format(current_os(), current_arch()),
                        choices=data.PLATFORMS.keys())
    parser.add_argument('--variant', type=str, help="Build variant to use instead of default")
    parser.add_argument('--cmake-extra', action='append', default=[])
    parser.add_argument('--coverage', action='store_true',
                        help="Enable test coverage report and upload it the codecov. Only supported when using cmake with gcc as compiler, error out on other cases.\n"
                        + "Use --coverage-include and --coverage-exclude to report the needed coverage file. The default code coverage report will include everything in the `source/` directory")
    parser.add_argument('--coverage-include', action='append', default=[],
                        help="The relative (based on the project directory) path of files and folders to include in the test coverage report.\n"
                        + "The default code coverage report will include everything in the `source/` directory")
    parser.add_argument('--coverage-exclude', action='append', default=[],
                        help="The relative (based on the project directory) path of files and folders (ends with `/`) to exlude from the test coverage report.\n"
                        + "The default code coverage report will include everything in the `source/` directory")

    # hand parse command and spec from within the args given
    command = None
    spec = None
    argv = sys.argv[1:]

    # eat command and optionally spec
    if argv and not argv[0].startswith('-'):
        command = argv.pop(0)
        if len(argv) >= 1 and not argv[0].startswith('-'):
            spec = argv.pop(0)

    if not command:
        if '-h' in argv or '--help' in argv:
            parser.print_help()
        else:
            print('No command provided, should be [build|inspect|<action-name>]')
        sys.exit(1)

    # parse the args we know, put the rest in args.args for others to parse
    args, extra = parser.parse_known_args(argv)
    args.args = extra
    args.command = command
    args.spec = args.spec if args.spec else spec
    # Backwards compat for `builder run $action`
    if args.command == 'run':
        args.command = args.spec
        args.spec = None

    # pull out any k=v pairs
    config_vars = []
    for arg in args.args.copy():
        m = re.match(r'(\+?)([A-Za-z_0-9]+)=(.+)', arg)
        if m:
            config_vars.append((m.group(1), m.group(2), m.group(3)))
            args.args.remove(arg)

    args.cli_config = {'variables': {}}
    for plus, key, val in config_vars:
        if key in data.KEYS:
            val = coerce_arg(val)
            if isinstance(data.KEYS[key], list):
                # Treat list entries from CLI as '!' overrides, unless first entry starts with '+'
                if key not in args.cli_config and not plus:
                    key = '!' + key

                prev = args.cli_config.get(key, [])
                args.cli_config[key] = prev + [val]
            else:
                # not a list
                args.cli_config[key] = val
        else:
            # unknown keys are treated as variables
            args.cli_config['variables'][key] = val

    # normalize target
    if args.target:
        args.target = normalize_target(args.target)

    if args.spec:
        spec = BuildSpec(spec=args.spec, target=args.target)

    if args.compiler or args.target:
        compiler, version = ('default', 'default')
        if args.compiler:
            if '-' in args.compiler:
                compiler, version = args.compiler.split('-')
            else:
                compiler = args.compiler
        spec = str(spec) if spec else None
        spec = BuildSpec(compiler=compiler,
                         compiler_version=version, target=args.target, spec=spec)

    if not spec:
        spec = default_spec()

    return args, spec


def upload_test_coverage(env):
    try:
        token = env.shell.get_secret("codecov-token", env.project.name)
    except:
        print(
            f"No token found for {name}. Check https://app.codecov.io/github/awslabs/{name}/settings"
            " for token and add it to codecov-token in Secrets Manager."
            .format(name=env.project.name),
            file=sys.stderr
        )
        exit()
    # only works for linux for now
    env.shell.exec('curl', '-Os', 'https://uploader.codecov.io/latest/linux/codecov', check=True)
    env.shell.exec('chmod', '+x', 'codecov', check=True)
    include_args = UniqueList(['source/'])
    include_args += env.args.coverage_include
    exclude_args = UniqueList(env.args.coverage_exclude)
    uploader_args = []
    for include in include_args:
        include += '*'
        uploader_args.append('-f')
        uploader_args.append(include.replace("/", "#"))
    for exclude in exclude_args:
        exclude += '*'
        exclude = "!" + exclude
        uploader_args.append('-f')
        uploader_args.append(exclude.replace("/", "#"))
    # based on the way generated report, we only upload the report started with `source/`
    env.shell.exec('./codecov', '-t', token, uploader_args, check=True)


def main():
    args, spec = parse_args()

    if args.build_dir != '.':
        if not os.path.isdir(args.build_dir):
            os.makedirs(args.build_dir)
        os.chdir(args.build_dir)

    print('Working in {}'.format(os.getcwd()))

    if spec.target == current_os() and spec.arch == current_arch():
        inspect_host(spec)
    if args.command == 'inspect':
        sys.exit(0)

    # set up environment
    env = Env({
        'dryrun': args.dry_run,
        'args': args,
        'project': args.project,
        'branch': args.branch,
        'spec': spec,
        'variant': args.variant,
    })

    Scripts.load()

    if not env.project and args.command != 'mirror':
        print('No project specified and no project found in current directory')
        sys.exit(1)

    print('Using Spec:')
    print('  Host: {} {}'.format(spec.host, current_arch()))
    print('  Target: {} {}'.format(spec.target, spec.arch))
    print('  Compiler: {} {}'.format(spec.compiler, spec.compiler_version))

    if not env.config.get('enabled', True):
        raise Exception("The project is disabled in this configuration")

    if env.config.get('needs_compiler', True):
        env.toolchain = Toolchain(spec=env.spec)

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

    if args.coverage:
        upload_test_coverage(env)


if __name__ == '__main__':
    main()
