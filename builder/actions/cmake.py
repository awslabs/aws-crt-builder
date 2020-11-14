# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os
from pathlib import Path

from action import Action
from toolchain import Toolchain


# All dirs used should be relative to env.source_dir, as this is where the cross
# compilation will be mounting to do its work
def _project_dirs(env, project):
    if not project.resolved():
        print('Project is not resolved: {}'.format(project.name))

    source_dir = str(Path(project.path).relative_to(env.source_dir))
    build_dir = str(
        Path(os.path.join(env.build_dir, project.name)).relative_to(env.source_dir))
    # cross compiles are effectively chrooted to the source_dir, normal builds need absolute paths
    # or cmake gets lost because it wants directories relative to source
    if env.toolchain.cross_compile:
        install_dir = str(Path(env.install_dir).relative_to(env.source_dir))
    else:
        install_dir = env.install_dir
    return source_dir, build_dir, install_dir


def _build_project(env, project, build_tests=False):
    sh = env.shell
    config = project.get_config(env.spec)
    toolchain = env.toolchain
    # build dependencies first, let cmake decide what needs doing
    for dep in project.get_dependencies(env.spec):
        _build_project(env, dep)

    project_source_dir, project_build_dir, project_install_dir = _project_dirs(
        env, project)
    sh.mkdir(os.path.abspath(project_build_dir))

    # If cmake has already run, assume we're good
    if os.path.isfile(os.path.join(project_build_dir, 'CMakeCache.txt')):
        return

    # TODO These platforms don't succeed when doing a RelWithDebInfo build
    build_config = env.args.config
    if toolchain.host in ("al2012", "manylinux"):
        build_config = "Debug"

    # Set compiler flags
    compiler_flags = []
    if toolchain.compiler != 'default' and not toolchain.cross_compile:
        c_path = toolchain.compiler_path()
        cxx_path = toolchain.cxx_compiler_path()
        for opt, value in [('c', c_path), ('cxx', cxx_path)]:
            if value:
                compiler_flags.append(
                    '-DCMAKE_{}_COMPILER={}'.format(opt.upper(), value))

    cmake_args = [
        "-B{}".format(project_build_dir),
        "-H{}".format(project_source_dir),
        # "-Werror=dev",
        # "-Werror=deprecated",
        "-DCMAKE_INSTALL_PREFIX=" + project_install_dir,
        "-DCMAKE_PREFIX_PATH=" + project_install_dir,
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        "-DCMAKE_BUILD_TYPE=" + build_config,
        "-DBUILD_TESTING=" + ("ON" if build_tests else "OFF"),
        *compiler_flags,
    ] + project.cmake_args(env)

    # When cross compiling, we must inject the build_env into the cross compile container
    build_env = []
    if toolchain.cross_compile:
        build_env = ['{}={}\n'.format(key, val)
                     for key, val in config.get('build_env', {}).items()]
        with open(toolchain.env_file, 'a') as f:
            f.writelines(build_env)

    # configure
    sh.exec(*toolchain.shell_env, "cmake", cmake_args, check=True)

    parallel = ["--", "-j"]
    if toolchain.compiler == 'msvc':
        parallel = ['--', '-maxcpucount']
    # build
    sh.exec(*toolchain.shell_env, "cmake", "--build", project_build_dir, "--config",
            build_config, *parallel, check=True)

    # install
    sh.exec(*toolchain.shell_env, "cmake", "--build", project_build_dir, "--config",
            build_config, "--target", "install", check=True)


class CMakeBuild(Action):
    """ Runs cmake configure, build """

    def __init__(self, project):
        self.project = project

    def run(self, env):
        toolchain = env.toolchain
        sh = env.shell

        for d in (env.build_dir, env.deps_dir, env.install_dir):
            sh.mkdir(d)

        # BUILD
        build_tests = self.project.needs_tests(env)
        _build_project(env, self.project, build_tests)

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

        sh.pushd(project_build_dir)
        sh.exec(*toolchain.shell_env, "ctest",
                "--output-on-failure", check=True)
        sh.popd()

    def __str__(self):
        return 'ctest {} @ {}'.format(self.project.name, self.project.path)
