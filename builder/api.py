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

from vmod import VirtualModule
from shell import Shell
from env import Env
from action import Action
from scripts import Scripts
from project import Project, Import
from actions.cmake import CMakeBuild, CTestRun
from actions.git import DownloadSource, DownloadDependencies
from actions.install import InstallPackages, InstallCompiler
from actions.script import Script
from toolchain import Toolchain
import host
import util


class Host(object):
    current_os = host.current_os
    current_arch = host.current_arch
    current_host = host.current_host


class Util(object):
    where = util.where
    run_command = util.run_command


class Builder(VirtualModule):
    """ The interface available to scripts that define projects, builds, actions, or configuration """

    Shell = Shell
    Env = Env
    Action = Action

    Project = Project
    Import = Import
    Toolchain = Toolchain

    Host = Host

    # Actions
    CMakeBuild = CMakeBuild
    CTestRun = CTestRun
    DownloadDependencies = DownloadDependencies
    DownloadSource = DownloadSource
    InstallTools = InstallPackages  # backward compat, deprecated
    InstallPackages = InstallPackages
    InstallCompiler = InstallCompiler
    Script = Script

    Util = Util
