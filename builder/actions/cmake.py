# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os
import re
import shutil
from functools import lru_cache, partial
from pathlib import Path

from builder.core.action import Action
from builder.core.toolchain import Toolchain
from builder.core.util import UniqueList, run_command


@lru_cache(1)
def _find_cmake():
    for cmake_alias in ['cmake3', 'cmake']:
        cmake = shutil.which(cmake_alias)
        if cmake:
            return cmake
    raise Exception("cmake not found")


@lru_cache(1)
def _find_ctest():
    for ctest_alias in ['ctest3', 'ctest']:
        ctest = shutil.which(ctest_alias)
        if ctest:
            return ctest
    raise Exception("cmake not found")


def cmake_path(cross_compile=False):
    if cross_compile:
        return 'cmake'
    return _find_cmake()


def cmake_version(cross_compile=False):
    if cross_compile:
        return '3.17.1'
    output = run_command([cmake_path(), '--version'], quiet=True).output
    m = re.match(r'cmake(3?) version ([\d\.])', output)
    if m:
        return m.group(2)
    return None


def cmake_binary(cross_compile=False):
    if cross_compile:
        return 'cmake'
    return os.path.basename(_find_cmake())


def ctest_binary(cross_compile):
    if cross_compile:
        return 'ctest'
    return os.path.basename(_find_ctest())


def _cmake_path(self):
    return cmake_path(self.cross_compile)


def _cmake_version(self):
    return cmake_version(self.cross_compile)


def _cmake_binary(self):
    return cmake_binary(self.cross_compile)


def _ctest_binary(self):
    return ctest_binary(self.cross_compile)


Toolchain.cmake_path = _cmake_path
Toolchain.cmake_version = _cmake_version
Toolchain.cmake_binary = _cmake_binary
Toolchain.ctest_binary = _ctest_binary


def _project_dirs(env, project):
    if not project.resolved():
        raise Exception('Project is not resolved: {}'.format(project.name))

    source_dir = project.path
    build_dir = os.path.join(env.build_dir, project.name)
    install_dir = env.install_dir

    # cross compiles are effectively chrooted to the source_dir, normal builds need absolute paths
    # or cmake gets lost because it wants directories relative to source
    if env.toolchain.cross_compile:
        # all dirs used should be relative to env.source_dir, as this is where the cross
        # compilation will be mounting to do its work
        source_dir = str(Path(source_dir).relative_to(env.root_dir))
        build_dir = str(Path(build_dir).relative_to(env.root_dir))
        install_dir = str(Path(install_dir).relative_to(env.root_dir))

    return source_dir, build_dir, install_dir


def _build_project(env, project, cmake_extra, build_tests=False, args_transformer=None, coverage=False):
    sh = env.shell
    config = project.get_config(env.spec)
    toolchain = env.toolchain
    # build dependencies first, let cmake decide what needs doing
    for dep in project.get_dependencies(env.spec):
        _build_project(env, dep, cmake_extra)

    project_source_dir, project_build_dir, project_install_dir = _project_dirs(
        env, project)
    abs_project_build_dir = project_build_dir
    if not os.path.isabs(project_build_dir):
        abs_project_build_dir = os.path.join(env.root_dir, project_build_dir)
    sh.mkdir(abs_project_build_dir)

    # If cmake has already run, assume we're good
    if os.path.isfile(os.path.join(abs_project_build_dir, 'CMakeCache.txt')):
        return

    cmake = toolchain.cmake_binary()
    cmake_version = toolchain.cmake_version()
    assert cmake_version != None

    # TODO These platforms don't succeed when doing a RelWithDebInfo build
    build_config = env.args.config
    if toolchain.host in ("al2012", "manylinux"):
        build_config = "Debug"

    # Set compiler flags
    compiler_flags = []
    if toolchain.compiler != 'default' and toolchain.compiler != 'msvc' and not toolchain.cross_compile:
        c_path = toolchain.compiler_path()
        cxx_path = toolchain.cxx_compiler_path()
        for opt, value in [('c', c_path), ('cxx', cxx_path)]:
            if value:
                compiler_flags.append(
                    '-DCMAKE_{}_COMPILER={}'.format(opt.upper(), value))

    cmake_args = UniqueList([
        "-B{}".format(project_build_dir),
        "-H{}".format(project_source_dir),
        # "-Werror=dev",
        # "-Werror=deprecated",
        "-DAWS_WARNINGS_ARE_ERRORS=ON",
        "-DCMAKE_INSTALL_PREFIX=" + project_install_dir,
        "-DCMAKE_PREFIX_PATH=" + project_install_dir,
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        "-DCMAKE_BUILD_TYPE=" + build_config,
        "-DBUILD_TESTING=" + ("ON" if build_tests else "OFF"),
        *compiler_flags,
    ])
    # Merging in cmake_args from all upstream projects inevitably leads to duplicate arguments.
    # Using a UniqueList seems to solve the problem well enough for now.
    # TODO: this can lead to unpredictable results for cases where same flag is
    # set on and off multiple times. ex. Flag A is added to args with value On,
    # Off, On. With UniqueList last On will be removed and cmake will treat flag
    # as off. Without UniqueList cmake will treat it as on.
    cmake_args += project.cmake_args(env)
    cmake_args += cmake_extra
    if coverage:
        if c_path and "gcc" in c_path:
            # Tell cmake to add coverage related configuration. And make sure GCC is used to compile the project.
            # CMAKE_C_FLAGS for GCC to enable code coverage information.
            # COVERAGE_EXTRA_FLAGS="*" is configuration for gcov
            #   --preserve-paths: to include path information in the report file name
            #   --source-prefix `pwd`: to exclude the `pwd` from the file name
            cmake_args += [
                "-DCMAKE_C_FLAGS=-fprofile-arcs -ftest-coverage",
                "-DCOVERAGE_EXTRA_FLAGS=--preserve-paths --source-prefix `pwd`"
            ]
        else:
            raise Exception('--coverage only support GCC as compiler. Current compiler is: {}'.format(c_path))

    # Allow caller to programmatically tweak the cmake_args,
    # as a last resort in case data merging wasn't working out
    if args_transformer:
        cmake_args = args_transformer(env, project, cmake_args)

    # When cross compiling, we must inject the build_env into the cross compile container
    build_env = []
    if toolchain.cross_compile:
        build_env = ['{}={}\n'.format(key, val)
                     for key, val in config.get('build_env', {}).items()]
        with open(toolchain.env_file, 'a') as f:
            f.writelines(build_env)

    # set parallism via env var (cmake's --parallel CLI option doesn't exist until 3.12)
    if os.environ.get('CMAKE_BUILD_PARALLEL_LEVEL') is None:
        sh.setenv('CMAKE_BUILD_PARALLEL_LEVEL', str(os.cpu_count()))

    working_dir = env.root_dir if toolchain.cross_compile else os.getcwd()

    # configure
    sh.exec(*toolchain.shell_env, cmake, cmake_args, working_dir=working_dir, check=True)

    # build & install
    sh.exec(*toolchain.shell_env, cmake, "--build", project_build_dir, "--config",
            build_config, "--target", "install", working_dir=working_dir, check=True)


class CMakeBuild(Action):
    """ Runs cmake configure, build """

    def __init__(self, project, *, args_transformer=None):
        self.project = project
        self.args_transformer = args_transformer

    def run(self, env):
        toolchain = env.toolchain
        sh = env.shell

        for d in (env.build_dir, env.deps_dir, env.install_dir):
            sh.mkdir(d)

        # BUILD
        build_tests = self.project.needs_tests(env)
        _build_project(env, self.project, env.args.cmake_extra, build_tests, self.args_transformer, env.args.coverage)

    def __str__(self):
        return 'cmake build {} @ {}'.format(self.project.name, self.project.path)


class CTestRun(Action):
    """ Uses ctest to run tests if tests are enabled/built via 'build_tests' """

    def __init__(self, project):
        self.project = project

    def run(self, env):
        sh = env.shell
        toolchain = env.toolchain

        if toolchain.cross_compile:
            print('WARNING: Running tests for cross compile is not yet supported')
            return

        project_source_dir, project_build_dir, project_install_dir = _project_dirs(
            env, self.project)

        if not os.path.isdir(project_build_dir):
            print("No build dir found, skipping CTest")
            return

        ctest = toolchain.ctest_binary()
        sh.exec(*toolchain.shell_env, ctest,
                "--output-on-failure", working_dir=project_build_dir, check=True)
        # Try to generate the coverage report. Will be ignored by ctest if no coverage data available.
        sh.exec(*toolchain.shell_env, ctest,
                "-T", "coverage", working_dir=project_build_dir, check=True)

    def __str__(self):
        return 'ctest {} @ {}'.format(self.project.name, self.project.path)
