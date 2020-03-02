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

# import all files in this directory
import importlib
from os.path import dirname, basename, isfile, join
import glob
import re
import sys
import zipfile

modules = []
try:
    # If running in a zipapp, we have to enumerate the zip app instead of the directory
    with zipfile.ZipFile(sys.argv[0]) as app:
        files = app.namelist()
        for f in files:
            print(f)
            if re.match(r'imports/[a-zA-Z0-9].+.py', f):
                modules += ['.' + basename(f)[:-3]]
except:
    # Must not be a zipapp, look on disk
    modules = glob.glob(join(dirname(__file__), "*.py"))
    modules = ['.' + basename(f)[:-3] for f in modules if isfile(f)
               and not f.endswith('__init__.py')]

for module in modules:
    print('Importing {}'.format(module[1:]))
    importlib.import_module(module, 'builder.imports')
