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
        # default the branch to whatever the current dir+git says it is
        self.branch = self._get_git_branch()

        # OVERRIDES: copy incoming config, overwriting defaults
        for key, val in config.items():
            setattr(self, key, val)

        # make sure the shell is initialized
        if not hasattr(self, 'shell'):
            self.shell = Shell(self.dryrun)

        # build environment set up
        self.source_dir = os.path.abspath(self.args.build_dir)
        self.build_dir = os.path.join(self.source_dir, 'build')
        self.deps_dir = os.path.join(self.build_dir, 'deps')
        self.install_dir = os.path.join(self.build_dir, 'install')
        self.launch_dir = os.path.abspath(self.shell.cwd())

        Project.search_dirs = [
            self.launch_dir,
            self.build_dir,
            self.source_dir,
            self.deps_dir,
        ]

        print('Source directory: {}'.format(self.source_dir))

        # default the project to whatever can be found, or convert
        # project from a name to a Project
        if not hasattr(self, 'project'):
            self.project = Project.default_project()

        if not self.project and not self.args.project:
            return

        project_name = self.project if self.project else self.args.project
        # Ensure that the specified project exists, this may return a ref or the project if
        # it is present on disk
        project = Project.find_project(project_name)
        if not project.path:  # got a ref
            print('Project {} could not be found locally, downloading'.format(
                project.name))
            DownloadSource(
                project=project, branch=self.branch).run(self)
            # Now that the project is downloaded, look it up again
            project = Project.find_project(project.name)
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
