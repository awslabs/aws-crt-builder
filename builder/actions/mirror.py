# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os
from action import Action
from project import Import


class Mirror(Action):
    """ Updates mirrored dependencies in S3/CloudFront """

    def is_main(self):
        return True

    def run(self, env):
        import_classes = Import.__subclasses__()

        for import_class in import_classes:
            imp = import_class()
            # only bother if the class actually implements mirror()
            if imp.__class__.__dict__.get('mirror', Import.__dict__['mirror']) != Import.__dict__['mirror']:
                print('Mirroring {}'.format(imp.name))
                imp.mirror(env)
