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

import os

from data import *
from host import current_platform

########################################################################################################################
# CONFIG
########################################################################################################################

# Ensure the combination of options specified are valid together


def validate_build(build_spec):

    assert build_spec.host in HOSTS, "Host name {} is invalid".format(
        build_spec.host)
    assert build_spec.target in TARGETS, "Target {} is invalid".format(
        build_spec.target)

    assert build_spec.compiler in COMPILERS, "Compiler {} is invalid".format(
        build_spec.compiler)
    compiler = COMPILERS[build_spec.compiler]

    assert build_spec.compiler_version in compiler['versions'], "Compiler version {} is invalid for compiler {}".format(
        build_spec.compiler_version, build_spec.compiler)

    supported_hosts = compiler['hosts']
    assert build_spec.host in supported_hosts or current_platform() in supported_hosts, "Compiler {} does not support host {}".format(
        build_spec.compiler, build_spec.host)

    supported_targets = compiler['targets']
    assert build_spec.target in supported_targets, "Compiler {} does not support target {}".format(
        build_spec.compiler, build_spec.target)

# Moved outside merge_dicts to avoid variable shadowing


def _apply_value(obj, key, new_value):

    key_type = type(new_value)
    if key_type == list:
        # Apply the config's value before the existing list
        obj[key] = new_value + obj[key]

    elif key_type == dict:
        # Iterate each element and recursively apply the values
        for k, v in new_value.items():
            _apply_value(obj[key], k, v)

    else:
        # Unsupported type, just use it
        obj[key] = new_value

# Replace all variable strings with their values


def replace_variables(value, variables):

    key_type = type(value)
    if key_type == str:

        # If the whole string is a variable, just replace it
        if value and value.rfind('{') == 0 and value.find('}') == len(value) - 1:
            return variables.get(value[1:-1], '')

        # Custom formatter for optional variables
        from string import Formatter

        class VariableFormatter(Formatter):
            def get_value(self, key, args, kwds):
                if isinstance(key, str):
                    return kwds.get(key, '')
                else:
                    return super().get_value(key, args, kwds)
        formatter = VariableFormatter()

        # Strings just do a format
        return formatter.format(value, **variables)

    elif key_type == list:
        # Update each element
        return [replace_variables(e, variables) for e in value]

    elif key_type == dict:
        # Iterate each element and recursively apply the variables
        return dict([(key, replace_variables(value, variables)) for (key, value) in value.items()])

    else:
        # Unsupported, just return it
        return value

# Traverse the configurations to produce one for the specified


def produce_config(build_spec, config_file, **additional_variables):

    platform = current_platform()

    defaults = {
        'hosts': HOSTS,
        'targets': TARGETS,
        'compilers': COMPILERS,
    }

    # Build the list of config options to poll
    configs = []

    # Processes a config object (could come from a file), searching for keys hosts, targets, and compilers
    def process_config(config):

        def process_element(map, element_name, instance):
            if not map:
                return

            element = map.get(element_name)
            if not element:
                return

            new_config = element.get(instance)
            if not new_config:
                return

            configs.append(new_config)

            config_archs = new_config.get('architectures')
            if config_archs:
                config_arch = config_archs.get(build_spec.arch)
                if config_arch:
                    configs.append(config_arch)

            return new_config

        # Get defaults from platform (linux) then override with host (al2, manylinux, etc)
        if platform != build_spec.host:
            process_element(config, 'hosts', platform)
        process_element(config, 'hosts', build_spec.host)
        process_element(config, 'targets', build_spec.target)

        compiler = process_element(config, 'compilers', build_spec.compiler)
        process_element(compiler, 'versions', build_spec.compiler_version)

    # Process defaults first
    process_config(defaults)

    # then override with config file
    if config_file:
        if not os.path.exists(config_file):
            raise Exception(
                "Config file {} specified, but could not be found".format(config_file))

        import json
        with open(config_file, 'r') as config_fp:
            try:
                project_config = json.load(config_fp)
                process_config(project_config)
                if project_config not in configs:
                    configs.append(project_config)
            except Exception as e:
                print("Failed to parse config file", config_file, e)
                sys.exit(1)

    new_version = {
        'spec': build_spec,
    }
    # Iterate all keys and apply them
    for key, default in KEYS.items():
        new_version[key] = default

        for config in configs:
            override_key = '!' + key
            if override_key in config:
                # Handle overrides
                new_version[key] = config[override_key]

            elif key in config:
                # By default, merge all values (except strings)
                _apply_value(new_version, key, config[key])

    # Default variables
    replacements = {
        'host': build_spec.host,
        'compiler': build_spec.compiler,
        'version': build_spec.compiler_version,
        'target': build_spec.target,
        'arch': build_spec.arch,
        'cwd': os.getcwd(),
        **additional_variables,
    }

    # Pull variables from the configs
    for config in configs:
        if 'variables' in config:
            variables = config['variables']
            assert type(variables) == dict

            # Copy into the variables list
            for k, v in variables.items():
                replacements[k] = v

    # Post process
    new_version = replace_variables(new_version, replacements)
    new_version['variables'] = replacements

    return new_version
