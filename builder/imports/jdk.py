# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import glob
import os
from pathlib import Path
import tarfile
import zipfile

from builder.core.fetch import fetch_and_extract, mirror_package
from builder.core.project import Import
import builder.core.util as util

URLs = {
    'linux-armv6': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u232-b09/OpenJDK8U-jdk_arm_linux_hotspot_8u232b09.tar.gz',
    'linux-armv7': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u232-b09/OpenJDK8U-jdk_arm_linux_hotspot_8u232b09.tar.gz',
    'linux-armv8': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u242-b08/OpenJDK8U-jdk_aarch64_linux_hotspot_jdk8u242-b08.tar.gz',
    'linux-x64': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u242-b08/OpenJDK8U-jdk_x64_linux_hotspot_8u242b08.tar.gz',
    'windows-x64': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u242-b08/OpenJDK8U-jdk_x64_windows_hotspot_8u242b08.zip',
    'windows-x86': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u242-b08/OpenJDK8U-jdk_x86-32_windows_hotspot_8u242b08.zip',
    'macos-x64': 'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u242-b08/OpenJDK8U-jdk_x64_mac_hotspot_8u242b08.tar.gz',
    'macos-armv8': 'https://corretto.aws/downloads/resources/8.422.05.1/amazon-corretto-8.422.05.1-macosx-aarch64.tar.gz',
}


class JDK8(Import):
    def __init__(self, **kwargs):
        super().__init__(
            config={},
            **kwargs)
        self.path = None
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        sh = env.shell

        target = '{}-{}'.format(env.spec.target, env.spec.arch)

        cross_compile = util.deep_get(env, 'toolchain.cross_compile', False)

        # If this is a local build, check the local machine
        if not cross_compile or target not in URLs:
            javac_path = util.where('javac')
            if javac_path:
                javac_path = javac_path.replace('/bin/javac', '')
            prefixes = [javac_path, os.environ.get('JAVA_HOME', None)]
            required_files = [
                ['include/jni.h'],
                ['lib/**/libjvm.so', '**/lib/**/libjvm.so',
                    'lib/**/jvm.dll', '**/lib/**/jvm.dll'],
            ]
            found = 0

            for paths in required_files:
                path_found = False
                for path in paths:
                    for prefix in prefixes:
                        if not prefix:
                            continue
                        full_path = os.path.join(prefix, path)
                        if glob.glob(full_path, recursive=True):
                            found += 1
                            path_found = True
                            break
                    if path_found:
                        break

            if found >= len(required_files):
                print('Found existing JDK8 at {}'.format(prefix))
                self.path = prefix
                env.variables['java_home'] = self.path
                self.installed = True
                return

        if target not in URLs:
            raise EnvironmentError(
                'No pre-built binaries for {} are available, please install JDK8 or greater and set JAVA_HOME'.format(target))

        install_dir = os.path.join(env.deps_dir, self.name.lower())
        # If path is going to be relative, it has to be relative to the source directory
        self.path = str(Path(install_dir).relative_to(env.root_dir))
        print('Installing pre-built JDK binaries for {} to {}'.format(
            target, install_dir))

        sh.mkdir(install_dir)
        url = URLs[target]
        ext = '.tar.gz' if url.endswith('.tar.gz') else '.zip'
        filename = '{}/jdk8{}'.format(install_dir, ext)
        print('Downloading {}'.format(url))
        fetch_and_extract(url, filename, install_dir)
        os.remove(filename)

        jdk_home = glob.glob(os.path.join(install_dir, '*jdk*'))[0]
        assert jdk_home

        # OSX is special and has a Contents/Home folder inside the distro
        if env.spec.target == 'macos':
            jdk_home = os.path.join(jdk_home, 'Contents', 'Home')

        # Use absolute path for local, relative for cross-compile
        self.path = jdk_home
        if cross_compile:
            self.path = str(Path(os.path.join(install_dir, jdk_home)
                                 ).relative_to(env.root_dir))

        env.variables['java_home'] = self.path
        self.installed = True

    def mirror(self, env):
        for src_url in URLs.values():
            mirror_package(self.name, src_url)
