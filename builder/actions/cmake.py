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


class CMakeBuild(Action):
    """ Runs cmake configure, build """

    def run(self, env):
        toolchain = env.toolchain
        sh = env.shell

        # TODO These platforms don't succeed when doing a RelWithDebInfo build
        build_config = env.args.config
        if toolchain.host in ("al2012", "manylinux"):
            build_config = "Debug"

        source_dir = env.source_dir
        build_dir = env.build_dir
        deps_dir = env.deps_dir
        install_dir = env.install_dir

        for d in (build_dir, deps_dir, install_dir):
            sh.mkdir(d)

        config = getattr(env, 'config', {})
        env.build_tests = config.get('build_tests', True)

        def build_project(project, build_tests=False):
            # build dependencies first, let cmake decide what needs doing
            for dep in project.get_dependencies(env.spec):
                sh.pushd(dep.path)
                build_project(dep)
                sh.popd()

            project_source_dir = project.path
            project_build_dir = os.path.join(project_source_dir, 'build')
            sh.mkdir(project_build_dir)
            sh.pushd(project_source_dir)

            project_build_dir = str(Path(
                project_build_dir).relative_to(project_source_dir))
            project_source_dir = str(
                Path(project_source_dir).relative_to(sh.cwd()))

            # If cmake has already run, assume we're good
            if os.path.isfile(os.path.join(project_build_dir, 'CMakeCache.txt')):
                return

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
                "-H.",
                "-Werror=dev",
                "-Werror=deprecated",
                "-DCMAKE_INSTALL_PREFIX=" + install_dir,
                "-DCMAKE_PREFIX_PATH=" + install_dir,
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

            sh.popd()

        def build_projects(projects):
            sh.pushd(deps_dir)

            for proj in projects:
                project = Project.find_project(proj)
                sh.pushd(project.path)
                build_project(project)
                sh.popd()

            sh.popd()

        sh.pushd(source_dir)

        spec = env.spec
        build_projects([p.name for p in env.project.get_dependencies(spec)])

        # BUILD
        build_project(env.project, getattr(env, 'build_tests', False))

        if spec and spec.downstream:
            build_projects([p.name for p in env.project.get_consumers(spec)])

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

        project_source_dir = env.project.path
        project_build_dir = os.path.join(project_source_dir, 'build')
        sh.pushd(project_build_dir)

        sh.exec(*toolchain.shell_env, "ctest",
                "--output-on-failure", check=True)

        sh.popd()
