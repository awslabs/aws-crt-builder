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
import subprocess
import sys

from actions.git import DownloadSource
from project import Project
from scripts import Scripts
from shell import Shell


def looks_like_code(path):
    git_dir = os.path.isdir(os.path.join(path, '.git'))
    if git_dir:
        return True
    # maybe not committed yet?
    readme = glob.glob(os.path.join(path, 'README.*'))
    if readme:
        return True
    return False


class Env(object):
    """ Encapsulates the environment in which the build is running """

    def __init__(self, config={}):
        self._projects = {}

        # DEFAULTS
        self.dryrun = False  # overwritten by config
        # default the branch to whatever the current dir+git says it is
        self.branch = self._get_git_branch()

        # OVERRIDES: copy incoming config, overwriting defaults
        for key, val in config.items():
            setattr(self, key, val)

        # make sure the shell is initialized
        if not hasattr(self, 'shell'):
            self.shell = Shell(self.dryrun)

        # build environment set up
        self.source_dir = os.environ.get(
            "CODEBUILD_SRC_DIR", self.shell.cwd())
        self.build_dir = os.path.join(self.source_dir, self.args.build_dir)
        self.deps_dir = os.path.join(self.build_dir, 'deps')
        self.install_dir = os.path.join(self.build_dir, 'install')
        self.launch_dir = self.shell.cwd()

        print('Source directory: {}'.format(self.source_dir))

        # Once initialized, switch to the build dir for everything else
        self.shell.rm(self.build_dir)
        self.shell.mkdir(self.build_dir)
        self.shell.cd(self.build_dir)

        # default the project to whatever can be found, or convert
        # project from a name to a Project
        if not hasattr(self, 'project'):
            self.project = self._default_project()

        if not self.project and not self.args.project:
            print('No project specified and no project found in current directory')
            sys.exit(1)
        project_name = self.project if self.project else self.args.project1
        # Ensure that the specified project exists, this may return a ref or the project if
        # it is present on disk
        project = self.find_project(project_name)
        if not project.path:  # got a ref
            print('Project {} could not be found locally, downloading'.format(
                project.name))
            DownloadSource(
                project=project, branch=self.branch).run(self)
            # Now that the project is downloaded, look it up again
            project = self.find_project(project.name)
            assert project.path
        self.project = project

    @staticmethod
    def _get_git_branch():
        travis_pr_branch = os.environ.get("TRAVIS_PULL_REQUEST_BRANCH")
        if travis_pr_branch:
            print("Found branch:", travis_pr_branch)
            return travis_pr_branch

        github_ref = os.environ.get("GITHUB_REF")
        if github_ref:
            origin_str = "refs/heads/"
            if github_ref.startswith(origin_str):
                branch = github_ref[len(origin_str):]
                print("Found github ref:", branch)
                return branch

        branches = subprocess.check_output(
            ["git", "branch", "-a", "--contains", "HEAD"]).decode("utf-8")
        branches = [branch.strip('*').strip()
                    for branch in branches.split('\n') if branch]

        print("Found branches:", branches)

        for branch in branches:
            if branch == "(no branch)":
                continue

            origin_str = "remotes/origin/"
            if branch.startswith(origin_str):
                branch = branch[len(origin_str):]

            return branch

        return None

    def _cache_project(self, project):
        self._projects[project.name] = project
        Scripts.load(project.path)
        return project

    def _default_project(self):
        project = self._project_from_cwd()
        if project:
            return self._cache_project(project)
        if not self.args.project:
            print(
                "Multiple projects available and no project (-p|--project) specified")
            print("Available projects:", ', '.join(
                [p.__name__ for p in Project.__subclasses__()]))
            sys.exit(1)

        project_name = self.args.project
        projects = Project.__subclasses__()
        for project_cls in projects:
            if project_cls.__name__ == project_name:
                project = project_cls()
                project.path = self.shell.cwd()
                return self._cache_project(project)
        print("Could not find project named {}".format(project_name))
        sys.exit(1)

    def _project_from_cwd(self, name_hint=None):
        project_config = None
        project_config_file = os.path.abspath("builder.json")
        if os.path.exists(project_config_file):
            import json
            with open(project_config_file, 'r') as config_fp:
                try:
                    project_config = json.load(config_fp)
                except Exception as e:
                    print("Failed to parse config file",
                          project_config_file, e)
                    sys.exit(1)
                return self._cache_project(Project(**project_config, path=self.shell.cwd()))

        # load any builder scripts and check them
        print("No project file found at {}, loading scripts".format(
            project_config_file))
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
            project.path = self.shell.cwd()
            return self._cache_project(project)

        return None

    def find_project(self, name):
        """ Finds a project, either on disk, or makes a virtual one to allow for acquisition """
        project = self._projects.get(name, None)
        if project:
            return project

        sh = self.shell
        search_dirs = (os.path.abspath(self.launch_dir), os.path.abspath(
            os.path.join('.', name)), self.source_dir, os.path.join(self.deps_dir, name))

        for search_dir in search_dirs:
            if (os.path.basename(search_dir) == name) and os.path.isdir(search_dir):
                sh.pushd(search_dir)
                project = self._project_from_cwd(name)
                sh.popd()

                # might be a project without a config
                if not project and looks_like_code(search_dir):
                    project = self._cache_project(
                        Project(name=name, path=search_dir))
                    return project

        # Enough of a project to get started, note that this is not cached
        return Project(name=name)

    def _find_compiler_tool(self, name, versions):
        for version in versions:
            for pattern in ('{name}-{version}', '{name}-{version}.0'):
                exe = pattern.format(name=name, version=version)
                path = self.shell.where(exe)
                if path:
                    return path, version
        return None, None

    def find_gcc_tool(self, name, version=None):
        """ Finds gcc, gcc-ld, gcc-ranlib, etc at a specific version, or the latest one available """
        versions = [version] if version else list(range(8, 5, -1))
        return self._find_compiler_tool(name, versions)

    def find_llvm_tool(self, name, version=None):
        """ Finds clang, clang-tidy, lld, etc at a specific version, or the latest one available """
        versions = [version] if version else list(range(10, 6, -1))
        return self._find_compiler_tool(name, versions)
