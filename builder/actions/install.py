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
        self.packages = packages

    def run(self, env):
        config = env.config
        sh = env.shell

        if getattr(env.args, 'skip_install', False):
            return

        pkg_setup = config.get('pkg_setup', [])
        if pkg_setup:
            for cmd in pkg_setup:
                if isinstance(cmd, str):
                    cmd = cmd.split(' ')
                assert isinstance(list, cmd)
                sh.exec(cmd)

        pkg_update = config.get('pkg_update', None)
        if pkg_update:
            pkg_update = pkg_update.split(' ')
            sh.exec(pkg_update)

        pkg_install = config['pkg_install']
        pkg_install = pkg_install.split('')
        pkg_install += self.packages + config.get('packages', [])

        sh.exec(pkg_install)
