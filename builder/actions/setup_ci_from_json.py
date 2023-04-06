# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.action import Action
import os
import pathlib
import sys
import json
import tempfile


class SetupCIFromJSON(Action):
    current_folder = None
    config_json = None
    env_instance = None

    # NOTE: This is needed to keep the tmp files alive
    tmp_file_storage = []

    def _is_platform_windows(self):
        return sys.platform.startswith("win32") or sys.platform.startswith('cygwin')

    def _is_platform_linux(self):
        return sys.platform.startswith("linux") or sys.platform.startswith('freebsd')

    def _is_platform_macos(self):
        return sys.platform.startswith("darwin")

    def _process_environment_variables(self, json_environment_variables):
        print("Starting to process all environment variables in JSON...")

        for item in json_environment_variables:

            ############################################################
            # PRE-PROCESSING
            ############################################################

            environment_name = None
            environment_value = None

            if ('name' in item):
                environment_name = item['name']
            else:
                print("[SKIPPED]: Invalid environment variable in JSON: variable is missing name")
                continue

            try:
                ############################################################
                # CONDITIONS (starts with "condition_")
                ############################################################

                # Checks if the operating system is the given operating system. Passes of OS matches.
                # Valid JSON:
                #   'condition_os': {
                #       "os": "windows" OR "linux" OR "macos"
                #       "result_true": "fail" OR "skip" OR "ignore"
                #       "result_false": "fail" OR "skip" OR "ignore"
                #   }
                if ('condition_os' in item):
                    desired_os = item['condition_os']['os'].lower()
                    result_true = item['condition_os']['result_true'].lower()
                    result_false = item['condition_os']['result_false'].lower()
                    got_undesired = False

                    if (desired_os == "windows"):
                        if (not self._is_platform_windows()):
                            got_undesired = True
                    elif (desired_os == "linux"):
                        if (not self._is_platform_linux()):
                            got_undesired = True
                    elif (desired_os == "macos"):
                        if (not self._is_platform_macos()):
                            got_undesired = True
                    else:
                        print(f"[FAIL] {environment_name} [Condition OS] Unknown input OS!")
                        sys.exit(f"[FAIL] {environment_name} [Condition OS] Unknown input OS!")

                    if (got_undesired == True):
                        if (result_true == "skip"):
                            print(f"[SKIPPED] {environment_name} [Condition OS - TRUE]: OS is not the input OS")
                            continue
                        elif (result_true == "fail"):
                            sys.exit(f"[FAIL] {environment_name} [Condition OS - TRUE]: OS is not the input OS")
                        else:
                            print(f"[IGNORE] {environment_name} [Condition OS - TRUE]: OS is not the input OS")
                    else:
                        if (result_false == "skip"):
                            print(f"[SKIPPED] {environment_name} [Condition OS - FALSE]: OS is not the input OS")
                            continue
                        elif (result_false == "fail"):
                            sys.exit(f"[FAIL] {environment_name} [Condition OS - FALSE]: OS is not the input OS")
                        else:
                            print(f"[IGNORE] {environment_name} [Condition OS - FALSE]: OS is not the input OS")

                # Checks if the script is running in Codebuild. Passes if running in Codebuild
                # Valid JSON:
                #   'condition_codebuild': {
                #       "result_true": "fail" OR "skip" OR "ignore"
                #       "result_false": "fail" OR "skip" OR "ignore"
                #   }
                if ('condition_codebuild' in item):
                    result_true = item['condition_codebuild']['result_true'].lower()
                    result_false = item['condition_codebuild']['result_false'].lower()

                    if (self.env_instance.shell.getenv("CODEBUILD_BUILD_ID", None) == None):
                        if (result_true == 'skip'):
                            print(f"[SKIPPED] {environment_name} [Condition Codebuild - TRUE]: OS is not Codebuild")
                            continue
                        elif (result_true == 'fail'):
                            sys.exit(f"[FAIL] {environment_name} [Condition Codebuild - TRUE]: OS is not Codebuild")
                        else:
                            print(f"[IGNORE] {environment_name} [Condition Codebuild - TRUE]: OS is not Codebuild")
                    else:
                        if (result_false == 'skip'):
                            print(f"[SKIPPED] {environment_name} [Condition Codebuild - FALSE]: OS is not Codebuild")
                            continue
                        elif (result_false == 'fail'):
                            sys.exit(f"[FAIL] {environment_name} [Condition Codebuild - FALSE]: OS is not Codebuild")
                        else:
                            print(f"[IGNORE] {environment_name} [Condition Codebuild - FALSE]: OS is not Codebuild")

                ############################################################
                # INPUT (starts with "input_")
                ############################################################

                # NOTE: These options WILL override each other if multiple are present.
                # Example: 'secret' overrides whatver value is in 'data' because 'secret' is AFTER 'data',
                # so if both are present, 'secret' will be what is used and not 'data'.

                # Puts whatever data is in the JSON directly into the environment_value.
                # Valid JSON:
                #   'input_data': <whatever you want>
                if ('input_data' in item):
                    environment_value = item["value"]

                # Puts whatever data is in the given AWS Secret Name into the environment_value
                # Valid JSON:
                #   { 'secret': <AWS Secret Name Here> }
                if ('input_secret' in item):
                    try:
                        environment_value = self.env_instance.shell.get_secret(item['input_secret'])
                    except:
                        sys.exit(f"[FAIL] {environment_name} [Input Secret]: Exception ocurred trying to get secret")

                ############################################################
                # FILE (starts with "file_")
                ############################################################
                # Writes whatever is in environment_value to a file
                #
                # NOTE: The last file processing option's resulting filepath will override the value of environment_value
                #
                # NOTE: File processing will happen to for EACH file processing option without overrides.
                #       If you have multiple "file_" options, you will have multiple files.
                environment_file_path = None

                # Writes whatever is in environment_value to the exact filepath given.
                # Valid JSON:
                #   'file_specific': <Exact file path here>
                if ('file_specific' in item):
                    with open(item['file_specific'], 'w') as file:
                        # lgtm [py/clear-text-storage-sensitive-data]
                        file.write(environment_value)
                    environment_file_path = str(self.current_folder) + item['file_specific']

                # Writes whatever is in environment_value to the relative (according to the Python file) filepath given.
                # Valid JSON:
                #   'file_relative': <Relative file path here>
                if ('file_relative' in item):
                    with open(str(self.current_folder) + item['file_relative'], 'w') as file:
                        # lgtm [py/clear-text-storage-sensitive-data]
                        file.write(environment_value)
                    environment_file_path = str(self.current_folder) + item['file_relative']

                # Writes whatever is in environment_value to a temporary named file.
                # NOTE: The value you pass here doesn't matter, if it is present it WILL be written to a temporary file.
                # Valid JSON:
                #   'file_tmp': true OR false
                if ('file_tmp' in item):
                    tmp_file = tempfile.NamedTemporaryFile()
                    # lgtm [py/clear-text-storage-sensitive-data]
                    tmp_file.write(str.encode(environment_value))
                    tmp_file.flush()
                    self.tmp_file_storage.append(tmp_file)
                    environment_file_path = tmp_file.name

                # If a file was written to, then override environment_value to it
                if (environment_file_path != None):
                    environment_value = environment_file_path

            except Exception as ex:
                sys.exit(f"[FAIL] {environment_name}: Something threw an exception! "
                         "This is likely due to an invalid/incorrectly-formatted JSON file. "
                         "Exception: {ex}")

            ############################################################
            # POST-PROCESSING
            ############################################################

            if (environment_value == None):
                print(
                    f"[SKIPPED] {environment_name}: Invalid environment variable in JSON: No environment value could not be set")
                continue

            # Write the environment variable
            print(f"{environment_name}: Set successfully")
            # Set it with quiet=true so we do NOT print anything secret to the console
            self.env_instance.shell.setenv(environment_name, environment_value, quiet=True)

        print("Finished processing all environment variables in JSON.")

    def _process_json_file(self, json_filepath):
        # Open the JSON file
        json_filepath_abs = pathlib.Path(json_filepath).resolve()
        json_file_data_raw = ""
        with open(json_filepath_abs, "r") as json_file:
            json_file_data_raw = json_file.read()
        # Load the JSON file
        json_data = json.loads(json_file_data_raw)

        # Process Environment Variables
        json_environment_variables = json_data["environment_variables"]
        if (json_environment_variables != None):
            self._process_environment_variables(json_environment_variables)

    def run(self, env):

        # Get the executing folder
        self.current_folder = os.path.dirname(pathlib.Path(__file__).resolve())
        if sys.platform == "win32" or sys.platform == "cygwin":
            self.current_folder += "\\"
        else:
            self.current_folder += "/"

        # Cache the env
        self.env_instance = env

        # Get the JSON file from the env
        print("Parsing JSON file...")
        json_filepath = self.env_instance.shell.getenv("AWS_UNIT_TEST_JSON_FILE", None)
        if (json_filepath == None):
            sys.exit("Cannot parse JSON file: AWS_UNIT_TEST_JSON_FILE is not set")
        if (os.path.exists(json_filepath) == False):
            sys.exit("Cannot parse JSON file: AWS_UNIT_TEST_JSON_FILE does not point to a valid file")
        print("JSON file parsed.")

        print("Processing JSON file...")
        self._process_json_file(json_filepath)
        print("Processed JSON file.")
