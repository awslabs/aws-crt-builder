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


from string import Formatter


class VariableFormatter(Formatter):
    """ Custom formatter for optional variables """

    def get_value(self, key, args, kwds):
        if isinstance(key, str):
            return kwds.get(key, '')
        else:
            return super().get_value(key, args, kwds)


_formatter = VariableFormatter()


def replace_variables(value, variables):
    """ Replaces all variables in all strings that can be found in the supplied value """
    key_type = type(value)
    if key_type == str:

        # If the whole string is a variable, just replace it
        if value and value.rfind('{') == 0 and value.find('}') == len(value) - 1:
            return variables.get(value[1:-1], '')

        # Strings just do a format
        return _formatter.format(value, **variables)

    elif key_type == list:
        # Update each element
        return [replace_variables(e, variables) for e in value]

    elif key_type == dict:
        # Iterate each element and recursively apply the variables
        return dict([(key, replace_variables(value, variables)) for (key, value) in value.items()])

    else:
        # Unsupported, just return it
        return value


def dict_alias(tree, key, alias):
    """ At any level in the tree, if key is found, a new entry with name alias will reference it """
    # depth first, should result in the least tree traversal
    for val in tree.values():
        if isinstance(val, dict):
            dict_alias(val, key, alias)
    original_keys = list(tree.keys())
    for tkey in original_keys:
        if tkey == key:
            tree[alias] = tree[tkey]


def merge_unique_attrs(src, target):
    """ Returns target with any fields unique to src added to it """
    for key, val in src._asdict().items():
        if not hasattr(target, key):
            setattr(target, key, val)
    return target
