# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import sys
from builder.action import Action
from builder.scripts import Scripts
from builder.util import replace_variables, to_list


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
                cmd = replace_variables(cmd, env.config['variables'])
            elif cmd_type == list:
                cmd = [replace_variables(
                    sub, env.config['variables']) for sub in cmd]
            return cmd

        # Interpolate any variables
        self.commands = [_expand_vars(cmd) for cmd in self.commands]

        # Run each of the commands
        children = []
        for cmd in self.commands:
            cmd_type = type(cmd)
            # See if the string is actually an action
            if cmd_type == str:
                action_cls = Scripts.find_action(cmd)
                if action_cls:
                    cmd = action_cls()
                    cmd_type = type(cmd)

            if cmd_type == str:
                result = sh.exec(*cmd.split(' '))
                if result.returncode != 0:
                    print('Command failed, exiting')
                    sys.exit(12)
            elif cmd_type == list:
                result = sh.exec(*cmd)
                if result.returncode != 0:
                    print('Command failed, exiting')
                    sys.exit(12)
            elif isinstance(cmd, Action):
                Scripts.run_action(cmd, env)
            elif callable(cmd):
                children += to_list(cmd(env))
            else:
                print('Unknown script sub command: {}: {}', cmd_type, cmd)
                sys.exit(4)
        return children

    def __str__(self):
        if len(self.commands) == 0:
            return '{}'.format(self.name)
        if self.name != self.__class__.__name__:
            return '{}'.format(self.name)

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
                cmds.append(cmd.__name__)
            else:
                cmds.append("UNKNOWN: {}".format(cmd))
        return '{}: (\n{}\n)'.format(self.name, '\n\t'.join(cmds))
