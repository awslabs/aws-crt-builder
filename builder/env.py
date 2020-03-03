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

import os
import subprocess
import sys

from actions.git import DownloadSource
from project import Project
from shell import Shell


class Env(object):
    """ Encapsulates the environment in which the build is running """

    def __init__(self, config={}):
        # DEFAULTS
        self.dryrun = False  # overwritten by config

        env = self

        class Variables(dict):
            def __setitem__(self, item, value):
                super().__setitem__(item, value)
                env._publish_variable(item, value)
        self.variables = Variables()

        # OVERRIDES: copy incoming config, overwriting defaults
        for key, val in config.items():
            setattr(self, key, val)

        # default the branch to whatever the current dir+git says it is
        if not self.branch:
            self.branch = self._get_git_branch()

        # make sure the shell is initialized
        if not hasattr(self, 'shell'):
            self.shell = Shell(self.dryrun)

        # build environment set up
        self.launch_dir = os.path.abspath(self.shell.cwd())

        Project.search_dirs = [
            self.launch_dir,
        ]

        # default the project to whatever can be found, or convert
        # project from a name to a Project
        if not getattr(self, 'project', None):
            self.project = Project.default_project()

        if not self.args.project:
            return

        project_name = self.args.project

        # see if the project is a path, if so, split it and give the path as a hint
        hints = []
        parts = project_name.split(os.path.sep)
        if os.path.isabs(project_name):
            hints += [project_name]
        elif len(parts) > 1:
            project_path = os.path.abspath(os.path.join(*parts))
            hints += [project_path]
        project_name = parts[-1]

        # Ensure that the specified project exists, this may return a ref or the project if
        # it is present on disk
        project = Project.find_project(project_name, hints=hints)
        if not project.path:  # got a ref
            print('Project {} could not be found locally, downloading'.format(
                project.name))
            DownloadSource(
                project=project, branch=self.branch, path='.').run(self)
            # Now that the project is downloaded, look it up again
            project = Project.find_project(
                project.name, hints=[os.path.abspath('.')])
            assert project.resolved()
        self.project = project

        if not self.project or not self.project.resolved():
            return

        # Build the config object
        self.config = self.project.get_config(self.spec, self.args.cli_config)

        # Once initialized, switch to the source dir before running actions
        config = self.project.config
        self.source_dir = os.path.abspath(self.project.path)
        self.shell.cd(self.source_dir)

        # Allow these to be overridden by the project, and relative to source_dir if not absolute paths
        build_dir = os.path.abspath(self.config.get(
            'build_dir', os.path.join(self.source_dir, 'build')))
        self.build_dir = build_dir

        deps_dir = os.path.abspath(self.config.get(
            'deps_dir', os.path.join(self.build_dir, 'deps')))
        self.deps_dir = deps_dir

        install_dir = os.path.abspath(self.config.get(
            'install_dir', os.path.join(self.source_dir, 'install')))
        self.install_dir = os.path.join(self.build_dir, 'install')

        print('Source directory: {}'.format(self.source_dir))
        print('Build directory: {}'.format(self.build_dir))

        self.variables['source_dir'] = self.source_dir
        self.variables['build_dir'] = self.build_dir
        self.variables['deps_dir'] = self.deps_dir
        self.variables['install_dir'] = self.install_dir

        Project.search_dirs += [
            self.build_dir,
            self.source_dir,
            self.deps_dir,
        ]

        # set up build environment
        if os.path.exists(self.build_dir):
            self.shell.rm(self.build_dir)
        self.shell.mkdir(self.build_dir)

    def _publish_variable(self, var, value):
        Project._publish_variable(var, value)

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

        try:
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

                print('Working in branch: {}'.format(branch))
                return branch
        except:
            print("Current directory () is not a git repository".format(os.getcwd()))

        return 'master'
