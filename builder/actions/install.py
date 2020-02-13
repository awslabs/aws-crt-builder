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

from action import Action


class InstallTools(Action):
    """ Installs prerequisites to building """

    def __init__(self, *packages):
        self.packages = list(packages)

    def run(self, env):
        config = env.config
        sh = env.shell
        sudo = config.get('sudo', current_platform() == 'linux')
        sudo = ['sudo'] if sudo else []

        was_dryrun = sh.dryrun
        if '--skip-install' in env.args.args:
            sh.dryrun = True

        pkg_setup = config.get('pkg_setup', [])
        if pkg_setup:
            for cmd in pkg_setup:
                if isinstance(cmd, str):
                    cmd = cmd.split(' ')
                assert isinstance(cmd, list)
                sh.exec(*sudo, cmd)

        pkg_update = config.get('pkg_update', None)
        if pkg_update:
            pkg_update = pkg_update.split(' ')
            sh.exec(*sudo, pkg_update)

        pkg_install = config['pkg_install']
        pkg_install = pkg_install.split(' ')
        pkg_install += self.packages + config.get('packages', [])

        sh.exec(*sudo, pkg_install)

        if '--skip-install' in env.args.args:
            sh.dryrun = was_dryrun
