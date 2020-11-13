# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

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

        # Default config to whatever is on the command line, fill in later when project is loaded
        self.config = self.args.cli_config

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
        if len(parts) > 1:
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
        self.source_dir = os.path.abspath(self.project.path)
        self.variables['source_dir'] = self.source_dir
        self.shell.cd(self.source_dir)

        # Allow these to be overridden by the project, and relative to source_dir if not absolute paths
        build_dir = self.config.get(
            'build_dir', os.path.join(self.source_dir, 'build'))
        self.build_dir = os.path.abspath(build_dir)
        self.variables['build_dir'] = self.build_dir

        deps_dir = self.config.get(
            'deps_dir', os.path.join(self.build_dir, 'deps'))
        self.deps_dir = os.path.abspath(deps_dir)
        self.variables['deps_dir'] = self.deps_dir

        install_dir = self.config.get(
            'install_dir', os.path.join(self.build_dir, 'install'))
        self.install_dir = os.path.abspath(install_dir)
        self.variables['install_dir'] = self.install_dir

        print('Source directory: {}'.format(self.source_dir))
        print('Build directory: {}'.format(self.build_dir))

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
            star_branch = None
            for branch in branches.split('\n'):
                if branch and branch.startswith('*'):
                    star_branch = branch.strip('*').strip()
                    break
            branches = [branch.strip('*').strip()
                        for branch in branches.split('\n') if branch]

            print("Found branches:", branches)

            # if git branch says we're on a branch, that's it
            if star_branch:
                print('Working in branch: {}'.format(star_branch))
                return star_branch

            # pick the first one (it should be the only one, if it's a fresh sync)
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

        # git symbolic-ref --short HEAD
        return 'main'
