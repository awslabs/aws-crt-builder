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
