# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os
from builder.core.action import Action
from builder.core.project import Project

# Branches that should NOT try to match same-named branches in dependencies.
# Used for e.g. landing unrelated external PRs via a reused branch name;
# dependencies will be pulled from main instead.
NO_DEPENDENCY_BRANCH_MATCH = ['external-pr']


class DownloadSource(Action):
    """ Downloads the source for a given project """

    def __init__(self, **kwargs):
        self.project = kwargs['project']
        self.branch = kwargs.get('branch', 'main')
        self.path = os.path.abspath(os.path.join(
            kwargs.get('path', '.'), self.project.name))

    def run(self, env):
        if self.project.path:
            print('Project {} already exists on disk'.format(self.project.name))
            return

        sh = env.shell

        print('Cloning {} from git'.format(self.project))
        if os.path.exists(self.path):
            sh.rm(self.path)
        sh.exec("git", "clone", self.project.url,
                self.path, always=True, retries=3)
        sh.pushd(self.path)
        try:
            sh.exec("git", "checkout", self.branch,
                    always=True, quiet=True, check=True)
            print('Switched to branch {}'.format(self.branch))
        except:
            print("Project {} does not have a branch named {}, using main".format(
                self.project.name, self.branch))

        sh.exec('git', 'submodule', 'update',
                '--init', '--recursive', retries=3)

        # reload project now that it's on disk
        self.project = Project.find_project(self.project.name)
        sh.popd()


class DownloadDependencies(Action):
    """ Downloads the source for dependencies and consumers if necessary """

    def run(self, env):
        project = env.project
        sh = env.shell
        branch = env.branch
        if branch in NO_DEPENDENCY_BRANCH_MATCH:
            print('Branch {} opts out of dependency branch matching, using main for dependencies'.format(branch))
            branch = 'main'
        spec = env.spec
        deps = project.get_dependencies(spec)

        if spec.downstream:
            deps += project.get_consumers(spec)

        if deps:
            sh.rm(env.deps_dir)
            sh.mkdir(env.deps_dir)
            sh.pushd(env.deps_dir)

            while deps:
                dep = deps.pop(0)  # pop front
                dep_proj = Project.find_project(dep.name)
                if dep_proj.path:
                    continue

                dep_branch = branch if dep.revision is None else dep.revision
                DownloadSource(project=dep_proj, branch=dep_branch, path=env.deps_dir).run(env)

                # grab updated project, collect transitive dependencies/consumers
                dep_proj = Project.find_project(dep.name)
                deps = dep_proj.get_dependencies(spec) + deps  # push front
                if spec and spec.downstream:
                    deps += dep_proj.get_consumers(spec)  # push back

            sh.popd()
