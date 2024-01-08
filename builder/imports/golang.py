# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os
from pathlib import Path

from builder.core.fetch import fetch_and_extract, mirror_package
from builder.core.project import Import
import builder.core.util as util

# Only linux versions for now
URLs = {
    'linux-armv6': 'https://go.dev/dl/go1.21.5.linux-armv6l.tar.gz',
    'linux-armv7': 'https://go.dev/dl/go1.21.5.linux-armv6l.tar.gz',
    'linux-armv8': 'https://go.dev/dl/go1.21.5.linux-arm64.tar.gz',
    'linux-x86': 'https://go.dev/dl/go1.21.5.linux-386.tar.gz',
    'linux-x64': 'https://go.dev/dl/go1.21.5.linux-amd64.tar.gz',
    'openbsd-x64': 'https://go.dev/dl/go1.21.5.linux-amd64.tar.gz',
}


class GOLANG(Import):
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
            # run `go version`
            result = util.run_command('go', 'version')
            if result.returncode == 0:
                # check the version, we need version >=1.18
                version_str = result.output.split(" ")[2][2:]
                version_numbers = list(map(int, version_str.split('.')))
                compare_version_numbers = list(map(int, "1.18.0".split('.')))
                if version_numbers >= compare_version_numbers:
                    return

        if target not in URLs:
            raise EnvironmentError(
                'No pre-built binaries for {} are available, please install golang greater than 1.18'.format(target))

        install_dir = os.path.join(env.deps_dir, self.name.lower())
        # If path is going to be relative, it has to be relative to the source directory
        self.path = str(Path(install_dir).relative_to(env.root_dir))
        print('Installing pre-built golang binaries for {} to {}'.format(
            target, install_dir))

        sh.mkdir(install_dir)
        url = URLs[target]
        ext = '.tar.gz' if url.endswith('.tar.gz') else '.zip'
        filename = '{}/golang{}'.format(install_dir, ext)
        print('Downloading {}'.format(url))
        fetch_and_extract(url, filename, install_dir)
        os.remove(filename)

        # Set PATH
        go_path = '{}/go/bin'.format(install_dir)
        sh.setenv('PATH', '{}{}{}'.format(go_path, os.pathsep, sh.getenv('PATH')))

        self.installed = True

    def mirror(self, env):
        for src_url in URLs.values():
            mirror_package(self.name, src_url)
