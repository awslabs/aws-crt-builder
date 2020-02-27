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

import os
from pathlib import Path

from action import Action
from toolchain import Toolchain
from project import Project


# All dirs used should be relative to env.source_dir, as this is where the cross
# compilation will be mounting to do its work
def _project_dirs(env, project, base_dir=None):
    source_dir = str(Path(project.path).relative_to(env.source_dir))
    build_dir = os.path.join(base_dir if base_dir else source_dir, 'build')
    install_dir = str(Path(env.install_dir).relative_to(env.source_dir))
    return source_dir, build_dir, install_dir


def _build_project(env, project, build_tests=False, base_dir=None):
    sh = env.shell
    config = env.config
    toolchain = env.toolchain
    # build dependencies first, let cmake decide what needs doing
    for dep in project.get_dependencies(env.spec):
        sh.pushd(dep.path)
        _build_project(env, dep)
        sh.popd()

    project_source_dir, project_build_dir, project_install_dir = _project_dirs(
        env, project, base_dir)
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
        c_path = toolchain.compiler_path(env)
        cxx_path = toolchain.cxx_compiler_path(env)
        for opt, value in [('c', c_path), ('cxx', cxx_path)]:
            if value:
                compiler_flags.append(
                    '-DCMAKE_{}_COMPILER={}'.format(opt.upper(), value))

    cmake_flags = []
    if env.spec.target == 'linux':
        cmake_flags += [
            # Each image has a custom installed openssl build, make sure CMake knows where to find it
            "-DLibCrypto_INCLUDE_DIR=/opt/openssl/include",
            "-DLibCrypto_SHARED_LIBRARY=/opt/openssl/lib/libcrypto.so",
            "-DLibCrypto_STATIC_LIBRARY=/opt/openssl/lib/libcrypto.a",
        ]

    cmake_args = [
        "-B{}".format(project_build_dir),
        "-H{}".format(project_source_dir),
        "-Werror=dev",
        "-Werror=deprecated",
        "-DCMAKE_INSTALL_PREFIX=" + project_install_dir,
        "-DCMAKE_PREFIX_PATH=" + project_install_dir,
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        "-DCMAKE_BUILD_TYPE=" + build_config,
        "-DBUILD_TESTING=" + ("ON" if build_tests else "OFF"),
        *cmake_flags,
        *compiler_flags,
    ] + getattr(project, 'cmake_args', []) + config.get('cmake_args', [])

    # configure
    sh.exec(*toolchain.shell_env, "cmake", cmake_args, check=True)

    # build
    sh.exec(*toolchain.shell_env, "cmake", "--build", project_build_dir, "--config",
            build_config, check=True)

    # install
    sh.exec(*toolchain.shell_env, "cmake", "--build", project_build_dir, "--config",
            build_config, "--target", "install", check=True)


def _build_projects(env, projects):
    for proj in projects:
        project = Project.find_project(proj)
        _build_project(project)


class CMakeBuild(Action):
    """ Runs cmake configure, build """

    def run(self, env):
        toolchain = env.toolchain
        sh = env.shell

        for d in (env.build_dir, env.deps_dir, env.install_dir):
            sh.mkdir(d)

        config = getattr(env, 'config', {})
        env.build_tests = config.get('build_tests', True)

        sh.pushd(env.source_dir)

        spec = env.spec
        _build_projects(
            env, [p.name for p in env.project.get_dependencies(spec)])

        # BUILD
        _build_project(env, env.project, getattr(env, 'build_tests', False))

        if spec and spec.downstream:
            _build_projects(
                env, [p.name for p in env.project.get_consumers(spec)])

        sh.popd()


class CTestRun(Action):
    """ Uses ctest to run tests if tests are enabled/built via 'build_tests' """

    def run(self, env):
        has_tests = getattr(env, 'build_tests', False)
        if not has_tests:
            print("No tests were built, skipping test run")
            return

        run_tests = env.config.get('run_tests', True)
        if not run_tests:
            print("Tests are disabled for this configuration")
            return

        sh = env.shell
        toolchain = env.toolchain

        project_source_dir, project_build_dir, project_install_dir = _project_dirs(
            env, env.project)

        sh.pushd(env.source_dir)
        sh.exec(*toolchain.shell_env, "ctest", "--build-exe-dir", project_build_dir,
                "--output-on-failure", check=True)
        sh.popd()
