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

import glob
import os
from pathlib import Path
from urllib.parse import urlparse
import zipfile

from fetch import fetch_and_extract, mirror_package
from project import Import
from util import chmod_exec


ANDROID_NDK_VERSION = '16b'


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

        install_dir = os.path.join(
            env.deps_dir, 'android-ndk-r{}'.format(ANDROID_NDK_VERSION))
        # If path to NDK is going to be relative, it has to be relative to the
        # source directory
        self.prefix = str(Path(install_dir).relative_to(env.source_dir))
        # Export ndk_path
        env.variables['ndk_path'] = os.path.join('/work', self.prefix)
        print('Installing NDK r{} to {}'.format(
            ANDROID_NDK_VERSION, install_dir))

        sh.mkdir(install_dir)
        filename = '{}/ndk-r{}.zip'.format(install_dir, ANDROID_NDK_VERSION)
        # Extract to deps dir, because zip file contains android-ndk-r{version} directory
        fetch_and_extract(self.url, filename, env.deps_dir)
        binaries = glob.glob(
            os.path.join(self.prefix, 'toolchains/llvm/prebuilt/linux-x86_64/bin/*'))
        for binary in binaries:
            chmod_exec(binary)

        self.installed = True

    def mirror(self, env):
        mirror_package(self.name, self.url)
