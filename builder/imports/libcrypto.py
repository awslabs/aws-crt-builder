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
from project import Import


class LibCrypto(Import):

    def __init__(self, **kwargs):
        super().__init__(
            config={
                'targets': ['linux'],
                'build_steps': [],
                'test_steps': [],
            },
            url='https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-1.1.1-{os}-{arch}.tar.gz',
            **kwargs)
        self.prefix = '/opt/openssl'
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        sh = env.shell

        self.installed = True
        # If this is a local build, check the local machine
        if not env.toolchain.cross_compile:
            required_files = [
                ['include/openssl/crypto.h'],
                ['lib/libcrypto.a', 'lib64/libcrypto.a'],
                ['lib/libcrypto.so', 'lib64/libcrypto.so'],
            ]
            found = 0
            for paths in required_files:
                for path in paths:
                    full_path = os.path.join(self.prefix, path)
                    if os.path.isfile(full_path):
                        found += 1
                        break

            if found >= len(required_files):
                print('Found existing libcrypto at {}'.format(self.prefix))
                env.variables['libcrypto_path'] = self.prefix
                return

        install_dir = os.path.join(env.deps_dir, self.name)
        # If path to libcrypto is going to be relative, it has to be relative to the
        # launch directory
        self.prefix = str(Path(install_dir).relative_to(env.launch_dir))
        env.variables['libcrypto_path'] = self.prefix
        print('Installing pre-built libcrypto binaries for {}-{} to {}'.format(
            env.spec.target, env.spec.arch, install_dir))

        sh.mkdir(install_dir)
        url = self.url.format(os=env.spec.target, arch=env.spec.arch)
        sh.exec('curl', '-sSL',
                '-o', '{}/libcrypto.tar.gz'.format(install_dir), url, check=True)
        sh.mkdir(install_dir)
        sh.exec('tar', 'xzf', '{}/libcrypto.tar.gz'.format(install_dir),
                '-C', install_dir, check=True)

    def cmake_args(self, env):
        assert self.installed
        return super().cmake_args(env) + [
            "-DLibCrypto_INCLUDE_DIR={}/include".format(self.prefix),
            "-DLibCrypto_SHARED_LIBRARY={}/lib/libcrypto.so".format(
                self.prefix),
            "-DLibCrypto_STATIC_LIBRARY={}/lib/libcrypto.a".format(
                self.prefix),
        ]
