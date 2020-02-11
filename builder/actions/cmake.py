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

from action import Action
from toolchain import Toolchain


class CMakeBuild(Action):
    """ Runs cmake configure, build """

    def run(self, env):
        try:
            toolchain = env.toolchain
        except:
            try:
                toolchain = env.toolchain = Toolchain(
                    spec=env.args.build)
            except:
                toolchain = env.toolchain = Toolchain(default=True)

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
            for dep in [env.find_project(p.name) for p in project.get_dependencies(env.build_spec)]:
                sh.pushd(dep.path)
                build_project(dep)
                sh.popd()

            project_source_dir = project.path
            project_build_dir = os.path.join(project_source_dir, 'build')
            sh.mkdir(project_build_dir)
            sh.pushd(project_build_dir)

            # Set compiler flags
            compiler_flags = []
            if toolchain.compiler != 'default':
                compiler_path = toolchain.compiler_path(env)
                if compiler_path:
                    for opt in ['c', 'cxx']:
                        compiler_flags.append(
                            '-DCMAKE_{}_COMPILER={}'.format(opt.upper(), compiler_path))

                if config:
                    for opt, variable in {'c': 'CC', 'cxx': 'CXX'}.items():
                        if opt in config and config[opt]:
                            sh.setenv(variable, config[opt])

            cmake_args = [
                "-Werror=dev",
                "-Werror=deprecated",
                "-DCMAKE_INSTALL_PREFIX=" + install_dir,
                "-DCMAKE_PREFIX_PATH=" + install_dir,
                # Each image has a custom installed openssl build, make sure CMake knows where to find it
                "-DLibCrypto_INCLUDE_DIR=/opt/openssl/include",
                "-DLibCrypto_SHARED_LIBRARY=/opt/openssl/lib/libcrypto.so",
                "-DLibCrypto_STATIC_LIBRARY=/opt/openssl/lib/libcrypto.a",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                "-DCMAKE_BUILD_TYPE=" + build_config,
                "-DBUILD_TESTING=" + ("ON" if build_tests else "OFF"),
            ] + compiler_flags + getattr(project, 'cmake_args', []) + config.get('cmake_args', [])

            # configure
            sh.exec("cmake", cmake_args, project_source_dir)

            # build
            sh.exec("cmake", "--build", ".", "--config", build_config)

            # install
            sh.exec("cmake", "--build", ".", "--config",
                    build_config, "--target", "install")

            sh.popd()

        def build_projects(projects):
            sh.pushd(deps_dir)

            for proj in projects:
                project = env.find_project(proj)
                sh.pushd(project.path)
                build_project(project)
                sh.popd()

            sh.popd()

        sh.pushd(source_dir)

        build_projects(
            [p.name for p in env.project.get_dependencies(env.build_spec)])

        # BUILD
        build_project(env.project, getattr(env, 'build_tests', False))

        spec = getattr(env, 'build_spec', None)
        if spec and spec.downstream:
            build_projects(
                [p.name for p in env.project.get_consumers(env.build_spec)])

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

        project_source_dir = env.project.path
        project_build_dir = os.path.join(project_source_dir, 'build')
        sh.pushd(project_build_dir)

        sh.exec("ctest", "--output-on-failure")

        sh.popd()
