
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.fetch import fetch_script, fetch_and_extract
from builder.core.host import current_os, current_arch
from builder.core.project import Import
import builder.core.util as util
from builder.actions.install import InstallPackages
from builder.actions.script import Script

import stat
import os
import re


NVM = r"""\
#!/usr/bin/env bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm $*
"""

DEFAULT_VERSION = '12'


class NodeJS(Import):
    def __init__(self, **kwargs):
        super().__init__(
            compiler=True,
            config={
                'targets': ['linux'],
            },
            **kwargs)
        self.url = 'https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh'
        self.version = kwargs.get('version', DEFAULT_VERSION)

        self.nvm = 'nvm'
        self.installed = False

    def install(self, env):
        if self.installed or (util.where('node') and current_os() == 'windows'):
            return

        sh = env.shell

        self.install_dir = os.path.join(env.deps_dir, self.name)
        sh.mkdir(self.install_dir)

        if current_arch() == "x86":
            self.install_node_via_unofficial_build(env)
        else:
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
        if current_os() != 'windows':
            result = sh.exec(self.nvm, 'which', self.version, check=True)
            node_path = os.path.dirname(result.output)
            sh.setenv('PATH', '{}{}{}'.format(
                node_path, os.pathsep, sh.getenv('PATH')))
            sh.exec('echo $PATH', check=True)
        else:
            sh.exec('nvm', 'use', '10.16', check=True)
            sh.exec('refreshenv', check=True)

        sh.exec('node', '--version', check=True)

    def install_nvm_choco(self, env):
        sh = env.shell
        Script([InstallPackages(['nvm'],)]).run(env)
        env_script = r'{}\dump_env.bat'.format(self.install_dir)
        with open(env_script, 'w+') as script:
            script.writelines(
                [
                    'call refreshenv.cmd\n',
                    'set\n'
                ]
            )
            script.flush()
        result = sh.exec(env_script, check=True, quiet=True)
        lines = result.output.split('\n')
        vars = {}
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                vars[key.upper()] = value
        # Update path and NVM_* env vars
        sh.setenv('PATH', vars['PATH'])
        for key, value in vars.items():
            if key.startswith('NVM_'):
                sh.setenv(key, value)
        sh.exec('nvm', 'version', check=True)

    def install_nvm_sh(self, env):
        sh = env.shell
        print('Installing nvm and node {} via nvm'.format(self.version))

        # Download nvm
        filename = '{}/install-nvm.sh'.format(self.install_dir)
        print('Downloading {} to {}'.format(self.url, filename))
        fetch_script(self.url, filename)
        sh.exec(filename, check=True)

        # Install wrapper to run NVM
        run_nvm = '{}/run-nvm.sh'.format(self.install_dir)
        with open(run_nvm, 'w+') as nvm_sh:
            nvm_sh.write(NVM)
        os.chmod(run_nvm, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        self.nvm = run_nvm

    def install_node_via_unofficial_build(self, env):
        sh = env.shell
        print('Installing node build directly'.format(self.version))

        # Normaliz version format, please note 12.16.3 is the last version has x86 support
        def normalize_version(v):
            append_times = 0
            while re.match(r'^([0-9]+\.){2}[0-9]+$', v) == None:
                # Only try append sub version twice
                if append_times < 2:
                    v += ".0"
                    append_times += 1
                else:  # DEFAULT TO 12.0.0
                    return (DEFAULT_VERSION + ".0.0")
            return v

        version = normalize_version(self.version)
        url = "https://unofficial-builds.nodejs.org/download/release/v{}/node-v{}-{}-{}.tar.gz".format(
            version, version, current_os(), current_arch())
        package_name = "node-v{}-{}-{}".format(version, current_os(), current_arch())

        # Fetch the node build
        extra_path = '{}/node_install'.format(self.install_dir)
        package_path = '{}/node_package'.format(self.install_dir)
        fetch_and_extract(url, package_path, extra_path)

        # Set PATH
        node_path = '{}/{}/bin'.format(extra_path, package_name)
        sh.setenv('PATH', '{}{}{}'.format(node_path, os.pathsep, sh.getenv('PATH')))


class Node12(NodeJS):
    def __init__(self, **kwargs):
        super().__init__(version='12', **kwargs)


class Node14(NodeJS):
    def __init__(self, **kwargs):
        super().__init__(version='14', **kwargs)


class Node16(NodeJS):
    def __init__(self, **kwargs):
        super().__init__(version='16', **kwargs)


class Node18(NodeJS):
    def __init__(self, **kwargs):
        super().__init__(version='18', **kwargs)
