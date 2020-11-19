# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.vmod import VirtualModule
from builder.shell import Shell
from builder.env import Env
from builder.action import Action
from builder.scripts import Scripts
from builder.project import Project, Import
from builder.actions.cmake import CMakeBuild, CTestRun
from builder.actions.git import DownloadSource, DownloadDependencies
from builder.actions.install import InstallPackages, InstallCompiler
from builder.actions.script import Script
from builder.toolchain import Toolchain
import builder.host as host
import builder.util as util


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
