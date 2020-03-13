
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
from actions.install import InstallPackages
from actions.script import Script

import stat
import os
from urllib.request import urlretrieve


NVM = """\
#!/usr/bin/env bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm $*
"""


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
        self.nvm = 'nvm'
        self.installed = False

    def install(self, env):
        if self.installed:
            return

        self.install_dir = os.path.join(env.deps_dir, self.name)

        if current_os() == 'windows':
            self.install_nvm_choco(env)
        else:
            self.install_nvm_sh(env)

        self.install_node_via_nvm(env)

        self.installed = True

    def install_node_via_nvm(self, env):
        sh = env.shell
        # Install node
        sh.exec(self.nvm, 'install', self.version, check=True)

        # Fetch path to installed node, add to PATH
        result = sh.exec(self.nvm, 'which', self.version, check=True)
        node_path = os.path.dirname(result.output)
        sh.setenv('PATH', '{}{}{}'.format(
            node_path, os.pathsep, sh.getenv('PATH')))
        sh.exec('node', '--version', check=True)

    def install_nvm_choco(self, env):
        sh = env.shell
        Script([InstallPackages(['nvm'],)]).run(env)
        env_script = r'{}\dump_env.bat'.format(self.install_dir)
        with open(env_script, 'w+') as script:
            script.writelines(
                [
                    'call refreshenv.cmd',
                    'set'
                ]
            )
            script.flush()
        sh.exec('type', env_script, check=True)
        result = sh.exec(env_script, check=True)
        lines = result.output.split(os.linesep)
        vars = {}
        for line in lines:
            print(line)
            if '=' in line:
                key, value = line.split('=')
                vars[key.upper()] = value
        # Update path and NVM_* env vars
        sh.setenv('PATH', vars['PATH'])
        for key, value in vars:
            if key.startswith('NVM_'):
                sh.setenv(key, value)

    def install_nvm_sh(self, env):
        sh = env.shell
        print('Installing nvm and node {} via nvm'.format(self.version))

        # Download nvm
        filename = '{}/install-nvm.sh'.format(self.install_dir)
        print('Downloading {} to {}'.format(self.url, filename))
        sh.mkdir(self.install_dir)
        urlretrieve(self.url, filename)
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        sh.exec(filename, check=True)

        # Install wrapper to run NVM
        run_nvm = '{}/run-nvm.sh'.format(self.install_dir)
        with open(run_nvm, 'w+') as nvm_sh:
            nvm_sh.write(NVM)
        os.chmod(run_nvm, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        self.nvm = run_nvm
