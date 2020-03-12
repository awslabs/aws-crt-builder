
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

from host import current_os
from project import Import

import stat
import os
from urllib.request import urlretrieve


class NodeJS(Import):
    def __init__(self, **kwargs):
        super().__init__(
            compiler=True,
            config={
                'targets': ['linux'],
            },
            **kwargs)
        self.url = 'https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh'
        self.version = '10'
        self.installed = False

    def install(self, env):
        if self.installed:
            return

        sh = env.shell
        toolchain = env.toolchain

        install_dir = os.path.join(env.deps_dir, self.name)
        print('Installing nvm and node {} via nvm'.format(self.version))

        filename = '{}/install-nvm.sh'.format(install_dir)
        print('Downloading {} to {}'.format(self.url, filename))
        sh.mkdir(install_dir)
        urlretrieve(self.url, filename)
        os.chmod(filename, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH |
                 stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        sh.exec(filename, 'install', self.version, check=True)
        sh.exec('node', '--version', check=True)
        self.installed = True
