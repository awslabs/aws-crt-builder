# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.action import Action
from builder.core.host import current_os, current_arch
import json
import tempfile
import os

import builder.actions.setup_cross_ci_helpers as helpers

"""
A builder action used by several CRT repositories to setup a set of common, cross-repository
environment variables, secrets, files, etc. that is used to build up the testing environment.
"""


class CleanupCrossCICrtEnvironment(Action):

    def run(self, env):
        # Bail if not running tests
        env.shell.exec('softhsm2-util',
                       '--delete-token',
                       '--token', 'my-test-token',
                       '--pin', '0000')
