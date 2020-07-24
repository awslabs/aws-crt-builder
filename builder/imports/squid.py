# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from project import Import
from actions.install import InstallPackages
from actions.script import Script
from host import current_os
import os


class Squid(Import):
    def __init__(self, **kwargs):
        super().__init__(
            config={
                'targets': ['linux'],
            },
            **kwargs)
        self.installed = False

    def resolved(self):
        return True

    def _find(self, name, path):
        for root, dirs, files in os.walk(path):
            if name in files:
                return os.path.join(root, name)

    def install(self, env):
        if self.installed:
            return

        # linux only for now
        print('Installing squid')

        Script([InstallPackages(['squid'])], name='install squid').run(env)

        print('Starting squid')

        sh = env.shell
        squid_conf_file_path = self._find('squid.conf', '/etc')

        if env.config.get('sudo', current_os() == 'linux'):
            start_squid = ['sudo', 'squid3', '-YC', '-f', squid_conf_file_path]
            restart_squid = ['sudo', 'service', 'squid', 'restart']
        else:
            start_squid = ['squid', '-YC', '-f', squid_conf_file_path]
            restart_squid = ['service', 'squid', 'restart']

        sh.exec(start_squid, check=True)
        sh.exec(restart_squid, check=True)

        print('Squid started')

        self.installed = True
