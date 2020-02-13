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

import argparse

from action import Action
from host import current_platform


class InstallTools(Action):
    """ Installs prerequisites to building """

    def __init__(self, *packages):
        self.packages = list(packages)

    def run(self, env):
        config = env.config
        packages = self.packages + config.get('packages', [])
        if not packages:
            return

        print('Installing packages: {}'.format(', '.join(packages)))

        sh = env.shell
        sudo = config.get('sudo', current_platform() == 'linux')
        sudo = ['sudo'] if sudo else []

        parser = argparse.ArgumentParser()
        parser.add_argument('--skip-install', action='store_true')
        args = parser.parse_known_args(env.args.args)[0]

        was_dryrun = sh.dryrun
        if args.skip_install:
            sh.dryrun = True

        pkg_setup = config.get('pkg_setup', [])
        if pkg_setup:
            for cmd in pkg_setup:
                if isinstance(cmd, str):
                    cmd = cmd.split(' ')
                assert isinstance(cmd, list)
                sh.exec(*sudo, cmd, check=True)

        pkg_update = config.get('pkg_update', None)
        if pkg_update:
            pkg_update = pkg_update.split(' ')
            sh.exec(*sudo, pkg_update, check=True)

        pkg_install = config['pkg_install']
        pkg_install = pkg_install.split(' ')
        pkg_install += packages

        sh.exec(*sudo, pkg_install, check=True)

        if args.skip_install:
            sh.dryrun = was_dryrun
