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
from action import Action
from project import Project


class DownloadSource(Action):
    """ Downloads the source for a given project """

    def __init__(self, **kwargs):
        self.project = kwargs['project']
        self.branch = kwargs.get('branch', 'master')
        self.path = os.path.abspath(os.path.join(
            kwargs.get('path', '.'), self.project.name))

    def run(self, env):
        if self.project.path:
            print('Project {} already exists on disk'.format(project.name))
            return

        sh = env.shell

        sh.exec("git", "clone", self.project.url, self.path, always=True)
        sh.pushd(self.path)
        try:
            sh.exec("git", "checkout", self.branch, always=True)
        except:
            print("Project {} does not have a branch named {}, using master".format(
                self.project.name, self.branch))

        sh.exec('git', 'submodule', 'update', '--init')

        # reload project now that it's on disk
        self.project = Project.find_project(self.project.name)
        sh.popd()


class DownloadDependencies(Action):
    """ Downloads the source for dependencies and consumers if necessary """

    def run(self, env):
        project = env.project
        sh = env.shell
        branch = env.branch
        spec = env.build_spec
        deps = project.get_dependencies(spec)

        if spec.downstream:
            deps += project.downstream

        if deps:
            sh.rm(env.deps_dir)
            sh.mkdir(env.deps_dir)
            sh.pushd(env.deps_dir)

            while deps:
                dep = deps.pop()
                dep_proj = Project.find_project(dep.name)
                if dep_proj.path:
                    continue

                dep_branch = getattr(dep, 'revision', branch)
                DownloadSource(
                    project=dep_proj, branch=dep_branch, path=env.deps_dir).run(env)

                # grab updated project, collect transitive dependencies/consumers
                dep_proj = Project.find_project(dep.name)
                deps += dep_proj.get_dependencies(spec)
                if spec and spec.downstream:
                    deps += dep_proj.get_consumers(spec)
                sh.popd()

            sh.popd()
