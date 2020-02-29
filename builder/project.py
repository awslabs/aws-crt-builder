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

from data import *
from host import current_os, package_tool
from scripts import Scripts
from util import replace_variables, merge_unique_attrs, to_list
from actions.cmake import CMakeBuild, CTestRun
from actions.script import Script


def looks_like_code(path):
    git_dir = os.path.isdir(os.path.join(path, '.git'))
    if git_dir:
        return True
    # maybe not committed yet?
    readme = glob.glob(os.path.join(path, 'README.*'))
    if readme:
        return True
    return False


def _apply_value(obj, key, new_value):
    """ Merge values according to type """
    key_type = type(new_value)
    if key_type == list:
        # Apply the config's value before the existing list
        val = obj[key]
        obj[key] = (new_value + val) if val else new_value

    elif key_type == dict:
        # Iterate each element and recursively apply the values
        for k, v in new_value.items():
            _apply_value(obj[key], k, v)

    else:
        # Unsupported type, just use it
        obj[key] = new_value


def _coalesce_pkg_options(spec, config):
    """ Promotes specific package manager config to pkg_ keys, e.g. apt_setup -> pkg_setup """
    pkg_tool = package_tool(spec.host)
    for suffix, default in [('setup', []),  ('update', ''), ('install', '')]:
        tool_value = config.get('{}_{}'.format(
            pkg_tool.value, suffix), default)
        pkg_key = 'pkg_{}'.format(suffix)
        config[pkg_key] = tool_value + config.get(pkg_key, default)
    # overwrite packages/compiler_packages if there are overrides
    for key, default in [('packages', []), ('compiler_packages', [])]:
        tool_value = config.get('{}_{}'.format(
            pkg_tool.value, key), default)
        if tool_value:
            config[key] = tool_value
    return config


def produce_config(build_spec, project, overrides=None, **additional_variables):
    """ Traverse the configurations to produce one for the given spec """
    platform = current_os()

    defaults = {
        'hosts': HOSTS,
        'targets': TARGETS,
        'compilers': COMPILERS,
        'architectures': ARCHS,
    }

    # Build the list of config options to poll
    configs = []

    # Processes a config object (could come from a file), searching for keys hosts, targets, and compilers
    def process_config(config):

        def process_element(map, element_name, instance):
            if not map:
                return

            element = map.get(element_name)
            if not element:
                return

            new_config = element.get(instance)
            if not new_config:
                return

            configs.append(new_config)

            # target, host, and compiler can contain architectures
            config_archs = new_config.get('architectures')
            if config_archs:
                config_arch = config_archs.get(build_spec.arch)
                if config_arch:
                    configs.append(config_arch)

            return new_config

        # Pull out any top level defaults
        defaults = {}
        for key, value in config.items():
            if key not in ('hosts', 'targets', 'compilers', 'architectures'):
                defaults[key] = value
        if len(defaults) > 0:
            configs.append(defaults)

        # pull out arch
        process_element(config, 'architectures', build_spec.arch)

        # pull out any host named default, then spec platform and host to override
        process_element(config, 'hosts', 'default')
        # Get defaults from platform (linux) then override with host (al2, manylinux, etc)
        if platform != build_spec.host:
            process_element(config, 'hosts', platform)
        process_element(config, 'hosts', build_spec.host)

        # pull out default target, then spec target to override
        process_element(config, 'targets', 'default')
        target = process_element(config, 'targets', build_spec.target)

        # pull out spec compiler and version info
        compiler = process_element(config, 'compilers', build_spec.compiler)

        # Allow most specific resolves to come last
        process_element(compiler, 'versions', build_spec.compiler_version)

    # Process defaults first
    process_config(defaults)

    # then override with config file
    project_config = project.config
    process_config(project_config)

    new_version = {
        'spec': build_spec,
    }
    # Iterate all keys and apply them
    for key, default in KEYS.items():
        new_version[key] = default

        for config in configs:
            override_key = '!' + key
            if override_key in config:
                # Handle overrides
                new_version[key] = config[override_key]

            elif key in config:
                # By default, merge all values (except strings)
                _apply_value(new_version, key, config[key])

    new_version = _coalesce_pkg_options(build_spec, new_version)

    if overrides:
        for key, val in overrides.items():
            new_version[key] = val

    # Default variables
    replacements = {
        'host': build_spec.host,
        'compiler': build_spec.compiler,
        'version': build_spec.compiler_version,
        'target': build_spec.target,
        'arch': build_spec.arch,
        'cwd': os.getcwd(),
        **additional_variables,
    }

    # Pull variables from the configs
    for config in configs:
        if 'variables' in config:
            variables = config['variables']
            assert type(variables) == dict

            # Copy into the variables list
            for k, v in variables.items():
                replacements[k] = v

    # Post process
    new_version = replace_variables(new_version, replacements)
    new_version['variables'] = replacements
    new_version['__processed'] = True

    return new_version


def _build_project(project, env):
    children = []
    children += to_list(project.pre_build(env))
    children += to_list(project.build(env))
    children += to_list(project.post_build(env))
    children += to_list(project.install(env))
    return children


class Project(object):
    """ Describes a given library and its dependencies/consumers """

    search_dirs = []

    def __init__(self, **kwargs):
        self.account = kwargs.get('account', 'awslabs')
        self.name = kwargs['name']
        self.url = kwargs.get('url', "https://github.com/{}/{}.git".format(
            self.account, self.name))
        self.path = kwargs.get('path', None)

        # Convert project json references to ProjectReferences
        def _not_resolved(s):
            return False
        kwargs['upstream'] = [namedtuple('ProjectReference', list(u.keys())+['resolved'])(
            *u.values(), _not_resolved) for u in kwargs.get('upstream', [])]
        kwargs['downstream'] = [namedtuple('ProjectReference', list(d.keys())+['resolved'])(
            *d.values(), _not_resolved) for d in kwargs.get('downstream', [])]
        kwargs['imports'] = [namedtuple('ImportReference', ['name', 'resolved'])(
            i, _not_resolved) for i in kwargs.get('imports', [])]

        # Store args as the intial config, will be merged via get_config() later
        self.config = {**kwargs.get('config', {}), **kwargs}

        # Allow projects to augment search dirs
        for search_dir in self.config.get('search_dirs', []):
            Project.search_dirs.append(os.path.join(self.path, search_dir))

    def __repr__(self):
        return "{}: {}".format(self.name, self.url)

    def resolved(self):
        return self.path is not None

    def pre_build(self, env):
        imports = self.get_imports(env.spec)
        build_imports = []
        for i in imports:
            build_imports += _build_project(i, env)

        deps = self.get_dependencies(env.spec)
        build_deps = []
        for d in deps:
            build_deps += _build_project(d, env)
        all_steps = build_imports + build_deps + \
            env.config.get('pre_build_steps', [])
        if len(all_steps) == 0:
            return None
        return Script(all_steps, name='pre_build {}'.format(self.name))

    def build(self, env):
        build_project = []
        steps = self.config.get('build_steps', self.config.get('build', []))
        if isinstance(steps, list):
            steps = [s if s != 'build' else CMakeBuild(self) for s in steps]
            build_project = [Script(steps, name='build {}'.format(self.name))]

        if len(build_project) == 0:
            return None
        return Script(build_project, name='build project {}'.format(self.name))

    def build_consumers(self, env):
        build_consumers = []
        consumers = self.get_consumers(env.spec)
        for c in consumers:
            build_consumers += _build_project(c, env)
        if len(build_consumers) == 0:
            return None
        return Script(build_consumers, name='build consumers of {}'.format(self.name))

    def post_build(self, env):
        steps = env.config.get('post_build_steps', [])
        if len(steps) == 0:
            return None
        return Script(steps, name='post_build {}'.format(self.name))

    def test(self, env):
        has_tests = getattr(env, 'build_tests', False)
        run_tests = env.config.get('run_tests', True)
        if not has_tests or not run_tests:
            return

        steps = env.config.get('build_steps', env.config.get('build', []))
        if isinstance(steps, list):
            steps = [s if s != 'test' else CTestRun(self) for s in steps]
            test_project = [Script(steps, name='test {}'.format(self.name))]
        return Script(steps, name='test {}'.format(self.name))

    def install(self, env):
        """ Can be overridden to install a project from anywhere """
        pass

    def cmake_args(self, env):
        """ Can be overridden to export CMake flags to consumers """
        args = []
        for imp in self.get_imports(env.spec):
            args += imp.cmake_args(env)
        for dep in self.get_dependencies(env.spec):
            args += dep.cmake_args(env)
        args += self.config.get('cmake_args', [])
        return args

    # convert ProjectReference -> Project
    def _resolve_refs(self):
        def _resolve(refs):
            projects = []
            for r in refs:
                if not isinstance(r, Project) or not r.resolved():
                    if isinstance(r, str):
                        project = Project.find_project(r)
                    else:
                        project = Project.find_project(r.name)
                        project = merge_unique_attrs(r, project)

                projects.append(project)
            return projects

        # Resolve upstream and downstream references into their
        # real projects, making sure to retain any reference-specific
        # data stored on the ref (targets, etc)
        self.dependencies = _resolve(
            self.config.get('upstream', []))
        self.consumers = _resolve(
            self.config.get('downstream', []))
        self.imports = _resolve(self.config.get('imports', []))

    def get_imports(self, spec):
        self._resolve_refs()
        target = spec.target
        imports = []
        for i in self.imports:
            if not hasattr(i, 'targets') or target in getattr(i, 'targets', []):
                imports.append(i)
        return imports

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

    def get_config(self, spec, overrides=None, **additional_vars):
        if not self.config or not self.config.get('__processed', False):
            self.config = produce_config(
                spec, self, overrides, **additional_vars)
        return self.config

    # project cache
    _projects = {}

    @staticmethod
    def _publish_variable(var, value):
        for project in Project._projects.values():
            project.config = replace_variables(project.config, {var: value})

    @staticmethod
    def _find_project_class(name):
        projects = Project.__subclasses__()
        project_cls = None
        for p in projects:
            if p.__name__.lower() == name.lower():
                return p

    @staticmethod
    def _create_project(name, **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = name
        project_cls = Project._find_project_class(name)
        if project_cls:
            return project_cls(**kwargs)
        return Project(**kwargs)

    @staticmethod
    def _cache_project(project):
        Project._projects[project.name] = project
        if project.path:
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
                print('    Found project: {} at {}'.format(
                    project_config['name'], path))
                project = Project._create_project(
                    **project_config, path=path, config=project_config)
                return Project._cache_project(project)

        # load any builder scripts and check them
        Scripts.load()
        if name_hint:
            project_cls = Project._find_project_class(name_hint)
            if project_cls:
                project = project_cls(name=name_hint)
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
        if project and project.resolved():
            return project

        dirs = []
        for d in hints + Project.search_dirs:
            dirs.append(d)
            dirs.append(os.path.join(d, name))

        # remove duplicates when these overlap
        dirs = list(OrderedDict.fromkeys(dirs))

        for search_dir in dirs:
            #print('  Looking in {}'.format(search_dir))
            if (os.path.basename(search_dir) == name) and os.path.isdir(search_dir):
                project = Project._project_from_path(search_dir, name)

                if project:
                    return project

                # might be a project without a config
                if looks_like_code(search_dir):
                    print(
                        ('    Found source code that looks like a project at {}'.format(search_dir)))
                    project = Project._cache_project(
                        Project(name=name, path=search_dir))
                    return project

        if Project._find_project_class(name):
            return Project._cache_project(Project._create_project(name))

        # Enough of a project to get started, note that this is not cached
        return Project(name=name)
