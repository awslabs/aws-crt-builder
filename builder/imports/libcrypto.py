# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from fetch import fetch_and_extract
from host import current_host
from project import Import

import argparse
import os
from pathlib import Path
from shutil import copytree
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

        install_dir = os.path.join(env.deps_dir, self.name)

        def _use_libcrypto(path):
            if not self.installed:
                os.symlink(path, install_dir, True)
                self.installed = True
            # If path to libcrypto is going to be relative, it has to be relative to the
            # source directory
            self.prefix = str(Path(install_dir).relative_to(env.source_dir))
            env.variables['libcrypto_path'] = self.prefix

        parser = argparse.ArgumentParser()
        parser.add_argument('--libcrypto', default=None)
        args = parser.parse_known_args(env.args.args)[0]

        if args.libcrypto:
            print('Using custom libcrypto: {}'.format(args.libcrypto))
            return _use_libcrypto(args.libcrypto)

        # AL2012 has a pre-built libcrypto, since its linker is from another world
        if current_host() == 'al2012':
            print('Using image libcrypto: /opt/openssl')
            return _use_libcrypto('/opt/openssl')

        print('Installing pre-built libcrypto binaries for {}-{} to {}'.format(
            env.spec.target, env.spec.arch, install_dir))

        lib_version = '1.1.1'
        lib_os = env.spec.target
        if current_host() == 'manylinux' and env.spec.arch != 'armv8':
            lib_os = 'manylinux'
            lib_version = '1.0.2'
        url = self.url.format(version=lib_version,
                              os=lib_os, arch=env.spec.arch)
        filename = '{}/libcrypto.tar.gz'.format(install_dir)
        print('Downloading {}'.format(url))
        fetch_and_extract(url, filename, install_dir)
        print('Extracted {} to {}'.format(filename, install_dir))

        self.installed = True
        return _use_libcrypto(install_dir)

    def cmake_args(self, env):
        assert self.installed
        return super().cmake_args(env) + [
            "-DLibCrypto_INCLUDE_DIR={}/include".format(self.prefix),
            "-DLibCrypto_SHARED_LIBRARY={}/lib/libcrypto.so".format(
                self.prefix),
            "-DLibCrypto_STATIC_LIBRARY={}/lib/libcrypto.a".format(
                self.prefix),
        ]
