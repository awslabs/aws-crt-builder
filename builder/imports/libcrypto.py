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
from project import Project


OPENSSL_DIR = '/opt/openssl'


class LibCrypto(Project):

    def __init__(self, **kwargs):
        super().__init__(
            config={
                'targets': ['linux'],
                'build_steps': [],
                'test_steps': [],
            },
            **kwargs)

    def install(self, env):
        sh = env.shell

        required_files = [
            os.path.join(OPENSSL_DIR, 'include', 'openssl', 'crypto.h'),
            os.path.join(OPENSSL_DIR, 'lib', 'libcrypto.a'),
            os.path.join(OPENSSL_DIR, 'lib64', 'libcrypto.a'),
            os.path.join(OPENSSL_DIR, 'lib', 'libcrypto.so'),
            os.path.join(OPENSSL_DIR, 'lib64', 'libcrypto.so'),
        ]

        found = 0
        for f in required_files:
            if os.path.isfile(f):
                found += 1

        # Must find crypto.h plus 1 of each of the libs
        if found >= (len(required_files) / 2 + 1):
            print('libcrypto is already installed, skipping download')
            return

        url = self.url.format(os=env.spec.target, arch=env.spec.arch)
        sh.exec('curl', '-sSL',
                '--output={}/libcrypto.tar.gz'.format(env.build_dir), url)
        sh.mkdir(OPENSSL_DIR)
        sh.exec('tar', 'xzf', '{}/libcrypto.tar.gz'.format(env.build_dir),
                '-C', '/opt/openssl')

    def cmake_args(self, env):
        return super().cmake_args(self, env) + [
            "-DLibCrypto_INCLUDE_DIR={}/include".format(OPENSSL_DIR),
            "-DLibCrypto_SHARED_LIBRARY={}/lib/libcrypto.so".format(
                OPENSSL_DIR),
            "-DLibCrypto_STATIC_LIBRARY={}/lib/libcrypto.a".format(
                OPENSSL_DIR),
        ]
