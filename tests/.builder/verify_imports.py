# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import Builder

# By just loading this script, it should interrogate the environment and make sure that every class we expect exists

CLASSES = (
    Builder.Shell,
    Builder.Env,
    Builder.Action,
    Builder.Host,
    Builder.Project,
    Builder.Toolchain,
    Builder.CMakeBuild,
    Builder.CTestRun,
    Builder.DownloadDependencies,
    Builder.DownloadSource,
    Builder.InstallTools,
    Builder.Script
)

print('Found API classes available:')
for cls in CLASSES:
    assert cls and cls.__name__
    print(cls.__name__)
