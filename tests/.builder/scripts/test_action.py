# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import Builder


class Test(Builder.Action):
    def run(self, env):
        def _doit(env):
            sh = env.shell
            sh.exec('true', retries=3)
        return Builder.Script([_doit])
