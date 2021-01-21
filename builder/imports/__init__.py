# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

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
        # parent_package = 'builder.imports'
        files = app.namelist()
        for f in files:
            if re.match(r'builder/imports/[a-zA-Z0-9].+.py', f):
                modules += ['builder.imports.' + basename(f)[:-3]]
except:
    # Must not be a zipapp, look on disk
    modules = glob.glob(join(dirname(__file__), "*.py"))
    modules = ['builder.imports.' + basename(f)[:-3] for f in modules if isfile(f)
               and not f.endswith('__init__.py')]

for module in modules:
    importlib.import_module(module)
