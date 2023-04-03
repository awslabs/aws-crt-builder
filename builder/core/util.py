# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.


import copy
from collections import namedtuple, UserList
from collections.abc import Iterable
from functools import reduce
import os
import stat
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


def _dict_deep_get(dictionary, keys, default=None):
    """
    Get the value associated with the composite key if it exists, otherwiser returns the default
    e.g. _dict_deep_get(d, 'foo.bar.baz') == d['foo']['bar']['baz']
    """
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)


def _attr_deep_get(obj, keys, default=None):
    """
    Access the nested attribute value associated with the composite key if it exists, otherwiser returns the default
    e.g. _attr_deep_get(obj, 'foo.bar.baz') == obj.foo.bar.baz
    """
    try:
        return reduce(getattr, keys.split("."), obj)
    except AttributeError:
        return default


def deep_get(target, keys, default=None):
    """
    Access the value associated with the composite key if it exists, otherwise return the default.
    This works on both dictionaries or objec attributes
    """
    if isinstance(target, dict):
        return _dict_deep_get(target, keys, default)
    else:
        return _attr_deep_get(target, keys, default)


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


def chmod_exec(file_path):
    os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


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


def command_to_str(*command):
    cmds = _flatten_command(*command)
    if sys.platform == 'win32':
        cmds = [cmd.encode('ascii', 'ignore').decode()
                for cmd in cmds]
    return subprocess.list2cmdline(cmds)


def log_command(*command):
    print('>', command_to_str(*command), flush=True)


def run_command(*command, check=False, quiet=False, dryrun=False, retries=0, working_dir=None):
    if not quiet:
        log_command(*command)
    if dryrun:
        return None
    tries = retries + 1
    if not working_dir:
        working_dir = os.getcwd()

    output = None
    while tries > 0:
        tries -= 1
        try:
            cmd = command_to_str(*command)

            # force the working directory
            cwd = os.getcwd()
            os.chdir(working_dir)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                bufsize=0)  # do not buffer output
            with proc:

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
                    if not quiet:
                        print(line, end='', flush=True)
                    line = proc.stdout.readline()
                proc.wait()

                # restore working directory before exiting the function
                os.chdir(cwd)

                if proc.returncode != 0:
                    raise Exception(
                        f'Command exited with code {proc.returncode}')

                return ExecResult(proc.returncode, proc.pid, output)

        except Exception as ex:
            print('Failed to run {}: {}'.format(
                ' '.join(_flatten_command(*command)), ex))
            if check and tries == 0:
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

    hashes = {}
    for k, v in o.items():
        hashes[k] = content_hash(v)

    return hash(tuple(frozenset(sorted(hashes.items()))))


class UniqueList(UserList):
    """ A list that only allows unique items to be appended. Items are id'ed by hash via content_hash """

    def __init__(self, items=None):
        super().__init__()
        if items is None:
            items = []
        self._hashes = set()
        for item in items:
            self.append(item)

    def __delitem__(self, idx):
        hash = content_hash(self.data[idx])
        self._hashes.remove(hash)
        self.data.__delitem__(idx)

    def __setitem__(self, idx, value):
        hash = content_hash(value)
        if hash not in self._hashes:
            self._hashes.add(hash)
            self.data.__setitem__(idx, value)

    # This allows for a += [b] style appending
    def __iadd__(self, other):
        for item in other:
            self.append(item)
        return self

    def append(self, value):
        hash = content_hash(value)
        if hash not in self._hashes:
            self._hashes.add(hash)
            self.data.append(value)
