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
import zipfile

from fetch import fetch_and_extract
from project import Import


ANDROID_NDK_VERSION = '16b'
ANDROID_API_VERSION = '19'


class NDK(Import):

    def __init__(self, **kwargs):
        super().__init__(
            name='ndk-r{}'.format(ANDROID_NDK_VERSION),
            config={
                'targets': ['linux'],
                'build_steps': [],
                'test_steps': [],
            },
            url='https://dl.google.com/android/repository/android-ndk-r{}-linux-x86_64.zip'.format(
                ANDROID_NDK_VERSION),
            **kwargs)
        self.prefix = ''
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        sh = env.shell

        install_dir = os.path.join(env.deps_dir, self.name)
        # If path to libcrypto is going to be relative, it has to be relative to the
        # source directory
        self.prefix = str(Path(install_dir).relative_to(env.source_dir))
        # Export ndk_path
        env.variables['ndk_path'] = self.prefix
        print('Installing pre-built libcrypto binaries for {}-{} to {}'.format(
            env.spec.target, env.spec.arch, install_dir))

        sh.mkdir(install_dir)
        filename = '{}/ndk-r{}.zip'.format(install_dir, ANDROID_NDK_VERSION)
        fetch_and_extract(self.url, filename, install_dir)
        self.installed = True
