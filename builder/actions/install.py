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

    def run(self, env):
        config = env.config
        sh = env.shell

        if getattr(env.args, 'skip_install', False):
            return

        if config['use_apt']:
            # Install keys
            for key in config['apt_keys']:
                sh.exec("sudo", "apt-key", "adv", "--fetch-keys", key)

            # Add APT repositories
            for repo in config['apt_repos']:
                sh.exec("sudo", "apt-add-repository", repo)

            # Install packages
            if config['apt_packages']:
                sh.exec("sudo", "apt-get", "-qq", "update", "-y")
                sh.exec("sudo", "apt-get", "-qq", "install",
                        "-y", "-f", config['apt_packages'])

        if config['use_brew']:
            for package in config['brew_packages']:
                sh.exec("brew", "install", package)
