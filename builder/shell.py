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

from collections import namedtuple
import os
import shutil
import subprocess
import sys
import tempfile


class Shell(object):
    """ Virtual shell that abstracts away dry run and tracks/logs state """

    def __init__(self, dryrun=False):
        # Used in dry-run builds to track simulated working directory
        self._cwd = os.getcwd()
        # pushd/popd stack
        self.dir_stack = []
        self.env_stack = []
        self.dryrun = dryrun

    def _flatten_command(self, *command):
        # Process out lists
        new_command = []

        def _proc_segment(command_segment):
            e_type = type(command_segment)
            if e_type == str:
                new_command.append(command_segment)
            elif e_type == list or e_type == tuple:
                for segment in command_segment:
                    _proc_segment(segment)
        _proc_segment(command)
        return new_command

    def _log_command(self, *command):
        print('>', subprocess.list2cmdline(
            self._flatten_command(*command)), flush=True)

    def _run_command(self, *command, **kwargs):
        ExecResult = namedtuple('ExecResult', ['returncode', 'pid', 'output'])
        if not kwargs.get('quiet', False):
            self._log_command(*command)
        if not self.dryrun:
            try:
                proc = subprocess.Popen(
                    self._flatten_command(*command),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0)  # do not buffer output

                output = bytes("", 'UTF-8')
                line = proc.stdout.readline()
                while (line):
                    output += line
                    if not kwargs.get('quiet', False):
                        line = line.decode(encoding='UTF-8')
                        print(line, end='', flush=True)
                    line = proc.stdout.readline()
                proc.wait()

                return ExecResult(proc.returncode, proc.pid, output)

            except Exception as ex:
                print('Failed to run {}: {}'.format(
                    ' '.join(self._flatten_command(*command)), ex))
                if kwargs.get('check', False):
                    sys.exit(5)
                return ExecResult(-1, -1, ex)

    def _cd(self, directory):
        if self.dryrun:
            if os.path.isabs(directory) or directory.startswith('$'):
                self._cwd = directory
            else:
                self._cwd = os.path.join(self._cwd, directory)
        else:
            os.chdir(directory)

    def cd(self, directory):
        """ # Helper to run chdir regardless of dry run status """
        self._log_command("cd", directory)
        self._cd(directory)

    def pushd(self, directory):
        """ Equivalent to bash/zsh pushd """
        self._log_command("pushd", directory)
        self.dir_stack.append(self.cwd())
        self._cd(directory)

    def popd(self):
        """ Equivalent to bash/zsh popd """
        if len(self.dir_stack) > 0:
            self._log_command("popd", self.dir_stack[-1])
            self._cd(self.dir_stack[-1])
            self.dir_stack.pop()

    def mkdir(self, directory):
        """ Equivalent to mkdir -p $dir """
        self._log_command("mkdir", "-p", directory)
        if not self.dryrun:
            os.makedirs(directory, exist_ok=True)

    def mktemp(self):
        """ Makes and returns the path to a temp directory """
        if self.dryrun:
            return os.path.expandvars("$TEMP/build")

        return tempfile.mkdtemp()

    def cwd(self):
        """ Returns current working directory, accounting for dry-runs """
        if self.dryrun:
            return self._cwd
        else:
            return os.getcwd()

    def setenv(self, var, value):
        """ Set an environment variable """
        self._log_command(["export", "{}={}".format(var, value)])
        if not self.dryrun:
            os.environ[var] = value

    def getenv(self, var):
        """ Get an environment variable """
        return os.environ[var]

    def pushenv(self):
        """ Store the current environment on a stack, for restoration later """
        self._log_command(['pushenv'])
        self.env_stack.append(dict(os.environ))

    def popenv(self):
        """ Restore the environment to the state on the top of the stack """
        self._log_command(['popenv'])
        env = self.env_stack.pop()
        # clear out values that won't be overwritten
        for name, value in dict(os.environ).items():
            if name not in env:
                del os.environ[name]
        # write the old env
        for name, value in env.items():
            os.environ[name] = value

    def rm(self, path):
        """ Remove a file or directory """
        self._log_command(['rm', '-rf', path])
        if not self.dryrun:
            try:
                shutil.rmtree(path)
            except Exception as e:
                print("Failed to delete dir {}: {}".format(path, e))

    def where(self, exe, path=None):
        """ Platform agnostic `where executable` command """
        if exe is None:
            return None
        if path is None:
            path = os.environ['PATH']
        paths = path.split(os.pathsep)
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
                    return exe_path

        return None

    def exec(self, *command, **kwargs):
        """ Executes a shell command, or just logs it for dry runs """
        result = None
        if kwargs.get('always', False):
            prev_dryrun = self.dryrun
            self.dryrun = False
            result = self._run_command(
                *command, quiet=kwargs.get('quiet', False), check=kwargs.get('check', False))
            self.dryrun = prev_dryrun
        else:
            result = self._run_command(
                *command, quiet=kwargs.get('quiet', False), check=kwargs.get('check', False))
        return result
