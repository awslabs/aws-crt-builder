# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.vmod import VirtualModule
from builder.core.shell import Shell
from builder.core.env import Env
from builder.core.action import Action
from builder.core.scripts import Scripts
from builder.core.project import Project, Import
from builder.actions.cmake import CMakeBuild, CTestRun
from builder.actions.git import DownloadSource, DownloadDependencies
from builder.actions.install import InstallPackages, InstallCompiler
from builder.actions.script import Script
from builder.core.toolchain import Toolchain
from builder.core import host
from builder.core import util
from builder.actions.setup_cross_ci_crt_environment import SetupCrossCICrtEnvironment
from builder.actions.cleanup_cross_ci_crt_environment import CleanupCrossCICrtEnvironment


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
    SetupCrossCICrtEnvironment = SetupCrossCICrtEnvironment
    CleanupCrossCICrtEnvironment = CleanupCrossCICrtEnvironment
    Util = Util
