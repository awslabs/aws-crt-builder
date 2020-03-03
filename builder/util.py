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
            return kwds.get(key, '{}'.format('{' + key + '}'))
        else:
            return super().get_value(key, args, kwds)


_formatter = VariableFormatter()


def replace_variables(value, variables):
    """ Replaces all variables in all strings that can be found in the supplied value """
    key_type = type(value)
    if key_type == str:

        # If the whole string is a variable, just replace it
        if value and value.rfind('{') == 0 and value.find('}') == len(value) - 1:
            return variables.get(value[1:-1], value)

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
    if key in tree:
        tree[alias] = tree[key]


def tree_transform(tree, key, fn):
    """ At any level in the tree, if key is found, it will be transformed via fn """
    # depth first, should result in the least tree traversal
    for val in tree.values():
        if isinstance(val, dict):
            tree_transform(val, key, fn)
    if key in tree:
        tree[key] = fn(tree[key])


def isnamedtuple(x):
    """ namedtuples are subclasses of tuple with a list of _fields """
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple:
        return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple):
        return False
    return all(type(n) == str for n in f)


def merge_unique_attrs(src, target):
    """ Returns target with any fields unique to src added to it """
    src_dict = src._asdict() if isnamedtuple(src) else src.__dict__
    for key, val in src_dict.items():
        if not hasattr(target, key):
            setattr(target, key, val)
    return target


def to_list(val):
    """ Do whatever it takes to coerce val into a list, usually for blind concatenation """
    if isinstance(val, list):
        return val
    if not val:
        return []
    return [val]
