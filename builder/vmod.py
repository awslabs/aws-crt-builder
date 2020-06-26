# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from importlib.abc import Loader, MetaPathFinder
import importlib
import sys

###############################################################################
# Virtual Module
# borrow the technique from the virtualmod module, allows 'import Builder' in
# .builder/*.py local scripts
###############################################################################
_virtual_modules = dict()


class VirtualModuleMetaclass(type):
    def __init__(cls, name, bases, attrs):
        # Initialize the class
        super(VirtualModuleMetaclass, cls).__init__(name, bases, attrs)

        # Do not register VirtualModule
        if name == 'VirtualModule':
            return

        module_name = getattr(cls, '__module_name__', cls.__name__) or name
        module = VirtualModule.create_module(module_name)

        # Copy over class attributes
        for key, value in attrs.items():
            if key in ('__name__', '__module_name__', '__module__', '__qualname__'):
                continue
            setattr(module, key, value)


class VirtualModule(metaclass=VirtualModuleMetaclass):
    class Finder(MetaPathFinder):
        @staticmethod
        def find_spec(fullname, path, target=None):
            if fullname in _virtual_modules:
                return _virtual_modules[fullname].__spec__
            return None

        @staticmethod
        def invalidate_caches():
            pass

    class VirtualLoader(Loader):
        @staticmethod
        def create_module(spec):
            if spec.name not in _virtual_modules:
                return None

            return _virtual_modules[spec.name]

        @staticmethod
        def exec_module(module):
            module_name = module.__name__
            if hasattr(module, '__spec__'):
                module_name = module.__spec__.name

            sys.modules[module_name] = module

    @staticmethod
    def create_module(name):
        module_cls = type(sys)
        spec_cls = type(sys.__spec__)
        module = module_cls(name)
        setattr(module, '__spec__', spec_cls(
            name=name, loader=VirtualModule.VirtualLoader))
        _virtual_modules[name] = module
        return module


sys.meta_path.insert(0, VirtualModule.Finder)
