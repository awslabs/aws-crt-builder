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

import importlib
import glob
import os
import sys


Action = None
Project = None
Import = None


def _import_dynamic_classes():
    # Must late import project to avoid cyclic dependency
    global Action
    global Project
    global Import
    project = __import__('project')
    Project = getattr(project, 'Project')
    Import = getattr(project, 'Import')

    action = __import__('action')
    Action = getattr(action, 'Action')


def _get_all_dynamic_classes():
    _import_dynamic_classes()
    return set(
        Action.__subclasses__() +
        Project.__subclasses__() +
        Import.__subclasses__())


class Scripts(object):
    """ Manages loading, context, and running of per-project scripts """

    # Must cache all classes with a reference here, or the GC will murder them
    all_classes = set()

    @staticmethod
    def load(path='.'):
        """ Loads all scripts from ${path}/.builder/**/*.py to make their classes available """
        import importlib.util

        path = os.path.abspath(os.path.join(path, '.builder'))
        if not os.path.isdir(path):
            return

        print('Loading scripts from {}'.format(path))
        scripts = glob.glob(os.path.join(path, '*.py'))
        scripts += glob.glob(os.path.join(path, '**', '*.py'))

        # Update to get the latest action set right before we load
        existing_classes = _get_all_dynamic_classes()
        for script in scripts:
            if not script.endswith('.py'):
                continue

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
            # Must invalidate caches or sometimes the loaded classes won't be found
            # See: https://docs.python.org/3/library/importlib.html#importlib.invalidate_caches
            importlib.invalidate_caches()

            # Report newly loaded actions
            classes = frozenset(_get_all_dynamic_classes())
            new_classes = classes.difference(existing_classes)
            if new_classes:
                print("Imported {}".format(
                    ', '.join([c.__name__ for c in new_classes])))
                Scripts.all_classes.update(new_classes)

    @staticmethod
    def _find_actions():
        _import_dynamic_classes()
        _all_actions = set(Action.__subclasses__())
        return _all_actions

    @staticmethod
    def find_action(name):
        """ Finds any loaded action class by name and returns it """
        name = name.replace('-', '').lower()
        all_actions = Scripts._find_actions()
        for action in all_actions:
            if action.__name__.lower() == name:
                return action

    @staticmethod
    def run_action(action, env):
        """ Runs an action, and any generated child actions recursively """
        action_type = type(action)
        if action_type is str:
            try:
                action_cls = Scripts.find_action(action)
                action = action_cls()
            except:
                print("Unable to find action {} to run".format(action))
                all_actions = [a.__name__ for a in Scripts._find_actions()]
                print("Available actions: \n\t{}".format(
                    '\n\t'.join(all_actions)))
                sys.exit(2)

        print("Running: {}".format(action), flush=True)
        children = action.run(env)
        if children:
            if not isinstance(children, list) and not isinstance(children, tuple):
                children = [children]
            for child in children:
                Scripts.run_action(child, env)
        print("Finished: {}".format(action), flush=True)
