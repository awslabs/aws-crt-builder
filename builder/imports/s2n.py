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

from project import Project, Import


class S2N(Project, Import):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Import.__init__(
            self,
            library=True,
            account='awslabs',
            imports=['libcrypto'],
            config={
                'targets': ['linux'],
                'test_steps': [],
                'cmake_args': {
                    '-DS2N_NO_PQ_ASM=ON',
                },
            },
            **kwargs)
