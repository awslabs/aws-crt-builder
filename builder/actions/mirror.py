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
