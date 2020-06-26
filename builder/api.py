# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

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
