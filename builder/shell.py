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

from host import current_os
import util


class Shell(object):
    """ Virtual shell that abstracts away dry run and tracks/logs state """

    def __init__(self, dryrun=False):
        # Used in dry-run builds to track simulated working directory
        self._cwd = os.getcwd()
        # pushd/popd stack
        self.dir_stack = []
        self.env_stack = []
        self.dryrun = dryrun
        self.platform = current_os()

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
        util.log_command("cd", directory)
        self._cd(directory)

    def pushd(self, directory):
        """ Equivalent to bash/zsh pushd """
        util.log_command("pushd", directory)
        self.dir_stack.append(self.cwd())
        self._cd(directory)

    def popd(self):
        """ Equivalent to bash/zsh popd """
        if len(self.dir_stack) > 0:
            util.log_command("popd", self.dir_stack[-1])
            self._cd(self.dir_stack[-1])
            self.dir_stack.pop()

    def mkdir(self, directory):
        """ Equivalent to mkdir -p $dir """
        util.log_command("mkdir", "-p", directory)
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
        util.log_command(["export", "{}={}".format(var, value)])
        if not self.dryrun:
            os.environ[var] = value

    def getenv(self, var):
        """ Get an environment variable """
        return os.environ[var]

    def pushenv(self):
        """ Store the current environment on a stack, for restoration later """
        util.log_command(['pushenv'])
        self.env_stack.append(dict(os.environ))

    def popenv(self):
        """ Restore the environment to the state on the top of the stack """
        util.log_command(['popenv'])
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
        util.log_command(['rm', '-rf', path])
        if not self.dryrun:
            try:
                shutil.rmtree(path)
            except Exception as e:
                print("Failed to delete dir {}: {}".format(path, e))

    def where(self, exe, path=None, resolve_symlinks=True):
        """ Platform agnostic `where executable` command """
        return util.where(exe, path, resolve_symlinks)

    def exec(self, *command, **kwargs):
        """ 
        Executes a shell command, or just logs it for dry runs 
        Arguments:
            check: If true, raise an exception when execution fails
            retries: (default 1) How many times to try the command, useful for network commands
            quiet: Do not produce any output
        """
        result = None
        if kwargs.get('always', False):
            prev_dryrun = self.dryrun
            self.dryrun = False
            result = util.run_command(*command, **kwargs, dryrun=self.dryrun)
            self.dryrun = prev_dryrun
        else:
            result = util.run_command(*command, **kwargs, dryrun=self.dryrun)
        return result
