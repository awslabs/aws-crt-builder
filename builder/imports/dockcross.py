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

from host import current_os
from project import Import

from pathlib import Path
import os


class Dockcross(Import):
    def __init__(self, **kwargs):
        super().__init__(
            compiler=True,
            config={
                'targets': ['linux'],
            },
            **kwargs)
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        sh = env.shell
        toolchain = env.toolchain

        sudo = env.config.get('sudo', current_os() == 'linux')
        sudo = ['sudo'] if sudo else []

        print(
            'Installing cross-compile via dockcross for {}'.format(toolchain.platform))
        cross_compile_platform = env.config.get(
            'cross_compile_platform', toolchain.platform)
        result = sh.exec(
            'docker', 'run', 'dockcross/{}'.format(cross_compile_platform), quiet=True)
        # Strip off any output from docker itself
        output, shebang, script = result.output.partition('#!')
        script = shebang + script
        print(output)
        assert result.returncode == 0

        dockcross = os.path.abspath(os.path.join(
            env.build_dir, 'dockcross-{}'.format(cross_compile_platform)))
        Path(dockcross).touch(0o755)
        with open(dockcross, "w+t") as f:
            f.write(script)
        sh.exec('chmod', 'a+x', dockcross)

        # Write out build_dir/dockcross.env file to init the dockcross env with
        # other code can add to this
        dockcross_env = os.path.join(env.build_dir, 'dockcross.env')
        with open(dockcross_env, "w+") as f:
            f.write('#env for dockcross\n')
        toolchain.env_file = dockcross_env
        toolchain.shell_env = [
            dockcross, '-a', '--env-file={}'.format(dockcross_env)]

        self.installed = True
