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


import copy
from collections import namedtuple, UserList
from collections.abc import Iterable
import os
from string import Formatter
import subprocess
import sys
from time import sleep


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
        # Iterate each element and recursively apply the variables in place
        for key, val in value.items():
            value[key] = replace_variables(val, variables)
        return value

    else:
        # Unsupported, just return it
        return value


def list_unique(items):
    """ Given a list, return a new list with the unique items in order from the original list """
    uniq = set()
    return [i for i in items if str(i) not in uniq and (uniq.add(str(i)) or True)]


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


def where(exe, path=None, resolve_symlinks=True):
    """ Platform agnostic `where executable` command """

    if exe is None:
        return None
    if path is None:
        path = os.environ['PATH']
    path_split = ':' if sys.platform != 'win32' else ';'
    paths = path.split(path_split)
    extlist = ['']

    def is_executable(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    if sys.platform == 'win32':
        pathext = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(exe)
        if ext.lower() not in pathext:
            extlist = pathext
    for ext in extlist:
        exe_name = exe + ext
        for p in paths:
            exe_path = os.path.join(p, exe_name)
            if is_executable(exe_path):
                # Remove any symlinks
                return os.path.realpath(exe_path) if resolve_symlinks else os.path.abspath(exe_path)

    return None


ExecResult = namedtuple('ExecResult', ['returncode', 'pid', 'output'])
_retry_wait_secs = 3  # wait 3 seconds between retries of commands


def _flatten_command(*command):
    # Process out lists
    new_command = []

    def _proc_segment(command_segment):
        e_type = type(command_segment)
        if e_type == str:
            new_command.append(command_segment)
        elif e_type == list or e_type == tuple or isinstance(command_segment, Iterable):
            for segment in command_segment:
                _proc_segment(segment)
    _proc_segment(command)
    return new_command


def log_command(*command):
    print('>', subprocess.list2cmdline(
        _flatten_command(*command)), flush=True)


def run_command(*command, **kwargs):
    if not kwargs.get('quiet', False):
        log_command(*command)
    dryrun = kwargs.get('dryrun', False)
    if dryrun:
        return None
    tries = kwargs.get('retries', 1)

    output = None
    while tries > 0:
        tries -= 1
        try:
            cmds = _flatten_command(*command)
            if sys.platform == 'win32':
                cmds = [cmd.encode('ascii', 'ignore').decode()
                        for cmd in cmds]
            proc = subprocess.Popen(
                cmds,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=(sys.platform == 'win32'),
                bufsize=0)  # do not buffer output

            # Convert all output to strings, which makes it much easier to both print
            # and process, since all known uses of parsing output want strings anyway
            output = ""
            line = proc.stdout.readline()
            while (line):
                # ignore weird characters coming back from the shell (colors, etc)
                if not isinstance(line, str):
                    line = line.decode('ascii', 'ignore')
                # We're reading in binary mode, so no automatic newline translation
                if sys.platform == 'win32':
                    line = line.replace('\r\n', '\n')
                output += line
                if not kwargs.get('quiet', False):
                    print(line, end='', flush=True)
                line = proc.stdout.readline()
            proc.wait()

            if proc.returncode != 0:
                raise Exception(
                    'Command exited with code {}'.format(proc.returncode))

            return ExecResult(proc.returncode, proc.pid, output)

        except Exception as ex:
            print('Failed to run {}: {}'.format(
                ' '.join(_flatten_command(*command)), ex))
            if kwargs.get('check', False) and tries == 0:
                raise
            output = ex
            if tries > 0:
                print('Waiting {} seconds to try again'.format(
                    _retry_wait_secs))
                sleep(_retry_wait_secs)
    return ExecResult(-1, -1, output)


def content_hash(o):
    """
    Makes a hash from a dictionary, list, tuple or set to any level, that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
    """

    if isinstance(o, (set, tuple, list)):
        return tuple([content_hash(item) for item in o])
    elif not isinstance(o, dict):
        if isinstance(o, object) and hasattr(o, '__dict__'):
            return content_hash(o.__dict__)
        try:
            return hash(o)
        except:
            return hash(str(o))

    hashes = copy.deepcopy(o)
    for k, v in hashes.items():
        hashes[k] = content_hash(v)

    return hash(tuple(frozenset(sorted(hashes.items()))))


class UniqueList(UserList):
    def __init__(self, items=[]):
        super().__init__()
        self._hashes = set()
        for item in items:
            self.append(item)

    def __delitem__(self, idx):
        hash = content_hash(self.data[idx])
        self._hashes.remove(hash)
        self.data.__delitem__(idx)

    def __setitem__(self, idx, value):
        hash = content_hash(value)
        if not hash in self._hashes:
            self._hashes.add(hash)
            self.data.__setitem__(idx, value)

    def append(self, value):
        hash = content_hash(value)
        if not hash in self._hashes:
            self._hashes.add(hash)
            self.data.append(value)
