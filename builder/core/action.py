# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.


class Action(object):
    """ A build step """

    def is_main(self):
        """ Returns True if this action needs no external tasks run to set it up """
        return False

    def run(self, env):
        pass

    def __str__(self):
        return self.__class__.__name__
