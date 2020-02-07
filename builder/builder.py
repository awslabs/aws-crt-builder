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

import glob
import os
import sys

from vmod import VirtualModule
from shell import Shell
from env import Env
from actions.action import Action


class Builder(VirtualModule):
    """ The interface available to scripts that define projects, builds, actions, or configuration """
    # Must cache available actions or the GC will delete them
    all_actions = set()
    Shell = Shell
    Env = Env
    Action = Action

    def __init__(self):
        Builder.all_actions = set(Builder.Action.__subclasses__())
        self._load_scripts()

    @staticmethod
    def _load_scripts():
        """ Loads all scripts from ${cwd}/.builder/**/*.py to make their classes available """
        import importlib.util

        if not os.path.isdir('.builder'):
            return

        scripts = glob.glob('.builder/*.py')
        scripts += glob.glob('.builder/**/*.py')
        for script in scripts:
            # Ensure that the import path includes the directory the script is in
            # so that relative imports work
            script_dir = os.path.dirname(script)
            if script_dir not in sys.path:
                sys.path.append(script_dir)
            print("Importing {}".format(os.path.abspath(script)), flush=True)

            name = os.path.split(script)[1].split('.')[0]
            spec = importlib.util.spec_from_file_location(name, script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            actions = frozenset(Builder._find_actions())
            new_actions = actions.difference(Builder.all_actions)
            print("Imported {}".format(
                ', '.join([a.__name__ for a in new_actions])))
            Builder.all_actions.update(new_actions)

    @staticmethod
    def _find_actions():
        return Action.__subclasses__()

    @staticmethod
    def find_action(name):
        """ Finds any loaded action class by name and returns it """
        name = name.replace('-', '').lower()
        all_actions = Builder._find_actions()
        for action in all_actions:
            if action.__name__.lower() == name:
                return action

    @staticmethod
    def run_action(action, env):
        """ Runs an action, and any generated child actions recursively """
        action_type = type(action)
        if action_type is str:
            try:
                action_cls = Builder.find_action(action)
                action = action_cls()
            except:
                print("Unable to find action {} to run".format(action))
                all_actions = [a.__name__ for a in Builder._find_actions()]
                print("Available actions: \n\t{}".format(
                    '\n\t'.join(all_actions)))
                sys.exit(2)

        print("Running: {}".format(action), flush=True)
        children = action.run(env)
        if children:
            if not isinstance(children, list) and not isinstance(children, tuple):
                children = [children]
            for child in children:
                Builder.run_action(child, env)
        print("Finished: {}".format(action), flush=True)
