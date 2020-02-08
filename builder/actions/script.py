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

from build import Builder
from action import Action


class Script(Action):
    """ A build step that runs a series of shell commands or python functions """

    def __init__(self, commands, **kwargs):
        self.commands = commands
        self.name = kwargs.get('name', self.__class__.__name__)

    def run(self, env):
        sh = env.shell

        def _expand_vars(cmd):
            cmd_type = type(cmd)
            if cmd_type == str:
                cmd = _replace_variables(cmd, env.config['variables'])
            elif cmd_type == list:
                cmd = [_replace_variables(
                    sub, env.config['variables']) for sub in cmd]
            return cmd

        # Interpolate any variables
        self.commands = [_expand_vars(cmd) for cmd in self.commands]

        # Run each of the commands
        for cmd in self.commands:
            cmd_type = type(cmd)
            if cmd_type == str:
                sh.exec(cmd)
            elif cmd_type == list:
                sh.exec(*cmd)
            elif isinstance(cmd, Action):
                Builder.run_action(cmd, env)
            elif callable(cmd):
                return cmd(env)
            else:
                print('Unknown script sub command: {}: {}', cmd_type, cmd)
                sys.exit(4)

    def __str__(self):
        if len(self.commands) == 0:
            return 'Script({}): Empty'.format(self.name)
        cmds = []
        for cmd in self.commands:
            cmd_type = type(cmd)
            if cmd_type == str:
                cmds.append(cmd)
            elif cmd_type == list:
                cmds.append(' '.join(cmd))
            elif isinstance(cmd, Action):
                cmds.append(str(cmd))
            elif callable(cmd):
                cmds.append(cmd.__func__.__name__)
            else:
                cmds.append("UNKNOWN: {}".format(cmd))
        return 'Script({}): (\n\t{}\n)'.format(self.name, '\n\t'.join(cmds))
