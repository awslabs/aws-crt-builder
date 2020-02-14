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

from collections import namedtuple, OrderedDict
import glob
import os
import sys

from scripts import Scripts


def looks_like_code(path):
    git_dir = os.path.isdir(os.path.join(path, '.git'))
    if git_dir:
        return True
    # maybe not committed yet?
    readme = glob.glob(os.path.join(path, 'README.*'))
    if readme:
        return True
    return False


class Project(object):
    """ Describes a given library and its dependencies/consumers """

    search_dirs = []

    def __init__(self, **kwargs):
        self.upstream = self.dependencies = [namedtuple('ProjectReference', u.keys())(
            *u.values()) for u in kwargs.get('upstream', [])]
        self.downstream = self.consumers = [namedtuple('ProjectReference', d.keys())(
            *d.values()) for d in kwargs.get('downstream', [])]
        self.account = kwargs.get('account', 'awslabs')
        self.name = kwargs['name']
        self.url = "https://github.com/{}/{}.git".format(
            self.account, self.name)
        self.path = kwargs.get('path', None)
        self._resolved_refs = False

    def __repr__(self):
        return "{}: {}".format(self.name, self.url)

    # convert ProjectReference -> Project
    def _resolve_refs(self):
        if self._resolved_refs:
            return
        upstream = []
        for u in self.upstream:
            upstream.append(Project.find_project(u.name))
        self.upstream = self.dependencies = upstream
        downstream = []
        for d in self.downstream:
            downstream.append(Project.find_project(d.name))
        self.downstream = self.consumers = downstream

    def get_dependencies(self, spec):
        """ Gets dependencies for a given BuildSpec, filters by target """
        self._resolve_refs()
        target = spec.target
        deps = []
        for p in self.dependencies:
            if not hasattr(p, 'targets') or target in getattr(p, 'targets', []):
                deps.append(p)
        return deps

    def get_consumers(self, spec):
        """ Gets consumers for a given BuildSpec, filters by target """
        self._resolve_refs()
        target = spec.target
        consumers = []
        for c in self.consumers:
            if not hasattr(c, 'targets') or target in getattr(c, 'targets', []):
                consumers.append(c)
        return consumers

    # project cache
    _projects = {}

    @staticmethod
    def _cache_project(project):
        Project._projects[project.name] = project
        Scripts.load(project.path)
        return project

    @staticmethod
    def default_project():
        project = Project._project_from_path('.')
        if project:
            return Project._cache_project(project)
        return None

    @staticmethod
    def _project_from_path(path='.', name_hint=None):
        path = os.path.abspath(path)
        project_config = None
        project_config_file = os.path.join(path, "builder.json")
        if os.path.exists(project_config_file):
            import json
            with open(project_config_file, 'r') as config_fp:
                try:
                    project_config = json.load(config_fp)
                except Exception as e:
                    print("Failed to parse config file",
                          project_config_file, e)
                    sys.exit(1)

                if not project_config.get('name', None):
                    project_config['name'] = name_hint if name_hint else os.path.dirname(
                        os.getcwd())
                print('    Found project: {}'.format(project_config['name']))
                return Project._cache_project(Project(**project_config, path=path))

        # load any builder scripts and check them
        Scripts.load()
        projects = Project.__subclasses__()
        project_cls = None
        if len(projects) == 1:
            project_cls = projects[0]
        elif name_hint:  # if there are multiple projects, try to use the hint if there is one
            for p in projects:
                if p.__name__ == name_hint:
                    project_cls = p

        if project_cls:
            project = project_cls()
            project.path = path
            return Project._cache_project(project)

        return None

    @staticmethod
    def projects():
        return Project._projects.keys()

    @staticmethod
    def find_project(name, hints=[]):
        """ Finds a project, either on disk, or makes a virtual one to allow for acquisition """
        project = Project._projects.get(name, None)
        if project:
            return project

        print('Looking for project {}'.format(name))
        dirs = list(hints)
        for d in Project.search_dirs:
            dirs.append(d)
            dirs.append(os.path.join(d, name))

        # remove duplicates when these overlap
        dirs = list(OrderedDict.fromkeys(dirs))

        for search_dir in dirs:
            print('  Looking in {}'.format(search_dir))
            if (os.path.basename(search_dir) == name) and os.path.isdir(search_dir):
                project = Project._project_from_path(search_dir, name)

                if project:
                    return project

                # might be a project without a config
                if looks_like_code(search_dir):
                    print(('    Found source code that looks like a project'))
                    project = Project._cache_project(
                        Project(name=name, path=search_dir))
                    return project

        # Enough of a project to get started, note that this is not cached
        return Project(name=name)
