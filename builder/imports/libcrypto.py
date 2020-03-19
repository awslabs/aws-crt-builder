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

from fetch import fetch_and_extract
from host import current_host
from project import Import

import argparse
import os
from pathlib import Path
import time


class LibCrypto(Import):

    def __init__(self, **kwargs):
        super().__init__(
            library=True,
            config={
                'targets': ['linux'],
                'build_steps': [],
                'test_steps': [],
            },
            url='https://d19elf31gohf1l.cloudfront.net/_binaries/libcrypto/libcrypto-{version}-{os}-{arch}.tar.gz',
            **kwargs)
        self.prefix = '/opt/openssl'
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        sh = env.shell

        parser = argparse.ArgumentParser()
        parser.add_argument('--libcrypto', default=None)
        args = parser.parse_known_args(env.args.args)[0]

        if args.libcrypto:
            print('Using custom libcrypto: {}'.format(args.libcrypto))
            self.prefix = args.libcrypto
            self.installed = True
            return

        install_dir = os.path.join(env.deps_dir, self.name)
        # If path to libcrypto is going to be relative, it has to be relative to the
        # source directory
        self.prefix = str(Path(install_dir).relative_to(env.source_dir))
        env.variables['libcrypto_path'] = self.prefix
        print('Installing pre-built libcrypto binaries for {}-{} to {}'.format(
            env.spec.target, env.spec.arch, install_dir))

        sh.mkdir(install_dir)

        lib_version = '1.1.1'
        lib_os = env.spec.target
        if current_host() == 'manylinux':
            lib_os = 'manylinux'
            lib_version = '1.0.2'
        url = self.url.format(version=lib_version,
                              os=lib_os, arch=env.spec.arch)
        filename = '{}/libcrypto.tar.gz'.format(install_dir)
        print('Downloading {}'.format(url))
        fetch_and_extract(url, filename, install_dir)
        print('Extracted {} to {}'.format(filename, install_dir))

        self.installed = True

    def cmake_args(self, env):
        assert self.installed
        return super().cmake_args(env) + [
            "-DLibCrypto_INCLUDE_DIR={}/include".format(self.prefix),
            "-DLibCrypto_SHARED_LIBRARY={}/lib/libcrypto.so".format(
                self.prefix),
            "-DLibCrypto_STATIC_LIBRARY={}/lib/libcrypto.a".format(
                self.prefix),
        ]
