# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import importlib
import importlib.util
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


def _find_all_subclasses(cls):
    """ Recursively find all subclasses """
    subclasses = set(cls.__subclasses__())
    for sub in cls.__subclasses__():
        subclasses = subclasses | _find_all_subclasses(sub)
    return subclasses


def _get_all_dynamic_classes():
    _import_dynamic_classes()
    all_classes = set(
        _find_all_subclasses(Action) |
        _find_all_subclasses(Project) |
        _find_all_subclasses(Import))
    return all_classes


def _normalize_name(name):
    return name.replace('-', '').lower()


def _find_classes(parent):
    _import_dynamic_classes()
    classes = _find_all_subclasses(parent)
    return classes


def _find_subclass(parent, name):
    name = _normalize_name(name)
    all_classes = _find_classes(parent)
    parent_name = parent.__name__.lower()
    for cls in all_classes:
        cls_name = cls.__name__.lower()
        if cls_name.endswith(parent_name):
            cls_name = cls_name.replace(
                "{}".format(parent_name), "")
        if name == cls_name:
            return cls
    return None


class Scripts(object):
    """ Manages loading, context, and running of per-project scripts """

    # Must cache all classes with a reference here, or the GC will murder them
    all_classes = set()

    @staticmethod
    def load(path='.'):
        """ Loads all scripts from ${path}/.builder/**/*.py to make their classes available """

        if len(Scripts.all_classes) == 0:
            Scripts.all_classes = _get_all_dynamic_classes()

        # Load any classes from path
        path = os.path.abspath(os.path.join(path, '.builder'))
        if os.path.isdir(path):
            print('Loading scripts from {}'.format(path))
            scripts = glob.glob(os.path.join(path, '*.py'))
            scripts += glob.glob(os.path.join(path, '**', '*.py'))

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

        # Report newly loaded classes
        classes = frozenset(_get_all_dynamic_classes())
        new_classes = classes.difference(Scripts.all_classes)
        if new_classes:
            print("Imported {}".format(
                ', '.join([c.__name__ for c in new_classes])))
            Scripts.all_classes.update(new_classes)

    @staticmethod
    def find_action(name):
        """ Finds any loaded action class by name and returns it """
        _import_dynamic_classes()
        return _find_subclass(Action, name)

    @staticmethod
    def find_project(name):
        """ Finds any loaded project class by name and returns it """
        _import_dynamic_classes()
        return _find_subclass(Project, name)

    @staticmethod
    def find_import(name):
        """ Finds any loaded import class by name and returns it """
        _import_dynamic_classes()
        return _find_subclass(Import, name)

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
