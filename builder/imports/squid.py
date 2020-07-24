# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from project import Import
from actions.install import InstallPackages
from actions.script import Script
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
        sh.exec('squid3', '-YC', '-f', squid_conf_file_path, check=True)
        sh.exec('sudo', 'service', 'squid', 'restart', check=True)

        print('Squid started')

        self.installed = True
