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
    tmp_file_storage = []  # NOTE: This is needed to keep the tmp files alive

    def _process_environment_variables(self, json_environment_variables):
        print("Starting to process all environment variables in JSON...")

        for item in json_environment_variables:

            ############################################################
            # PRE-PROCESSING
            ############################################################

            environment_name = None
            environment_value = None

            if ('name' in item):
                environment_name = str(item['name'])
            else:
                print("[SKIPPED]: Invalid environment variable in JSON: variable is missing name")
                continue

            try:

                ############################################################
                # INPUT (starts with "input_")
                ############################################################

                # NOTE: These options WILL override each other if multiple are present.
                # Example: 'secret' overrides whatver value is in 'data' because 'secret' is AFTER 'data',
                # so if both are present, 'secret' will be what is used and not 'data'.

                # Puts whatever data is in the JSON directly into the environment_value.
                # Valid JSON:
                #   'input_data': <whatever input you want>
                if ('input_data' in item):
                    environment_value = str(item["input_data"])

                # Puts whatever data is in the given AWS Secret Name into the environment_value
                # Valid JSON:
                #   { 'input_secret': <AWS Secret Name Here> }
                if ('input_secret' in item):
                    try:
                        environment_value = self.env_instance.shell.get_secret(str(item['input_secret']))
                    except:
                        sys.exit(f"[FAIL] {environment_name} [Input Secret]: Exception ocurred trying to get secret")

                # Downloads the S3 file at the given URL and sets environment_value to the downloaded (temporary) file.
                # Valid JSON:
                #   { 'input_s3': <S3 URL Here> }
                if ('input_s3' in item):
                    try:
                        tmp_file = tempfile.NamedTemporaryFile()
                        tmp_file.flush()
                        self.tmp_file_storage.append(tmp_file)
                        tmp_s3_filepath = tmp_file.name
                        self.copy_s3_file(str(item['input_s3']), tmp_s3_filepath)
                        environment_value = str(tmp_s3_filepath)
                    except Exception as ex:
                        print(ex)
                        sys.exit(f"[FAIL] {environment_name} [Input S3]: Exception ocurred trying to get S3 file")

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
                    with open(str(item['file_specific']), 'w') as file:
                        # lgtm [py/clear-text-storage-sensitive-data]
                        file.write(environment_value)
                    environment_file_path = str(item['file_specific'])

                # Writes whatever is in environment_value to the relative (according to the Python file) filepath given.
                # Valid JSON:
                #   'file_relative': <Relative file path here>
                if ('file_relative' in item):
                    with open(str(self.current_folder) + str(item['file_relative']), 'w') as file:
                        # lgtm [py/clear-text-storage-sensitive-data]
                        file.write(environment_value)
                    environment_file_path = str(self.current_folder) + str(item['file_relative'])

                # Writes whatever is in environment_value to a temporary named file.
                # NOTE: The value you pass here doesn't matter, if it is present it WILL be written to a temporary file.
                # Valid JSON:
                #   'file_tmp': <whatever you want - its unused>
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
                         f"Exception: {ex}")

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
        try:
            json_data = json.loads(json_file_data_raw)
        except:
            sys.exit(f"[FAIL]: Exception ocurred trying parson JSON file with name {json_filepath}")

        # Process Environment Variables
        self._process_environment_variables(json_data)

    def copy_s3_file(self, s3_url, filename):
        cmd = ['aws', '--region', 'us-east-1', 's3', 'cp',
               s3_url, filename]
        self.env_instance.shell.exec(*cmd, check=True, quiet=True)

    def run(self, env):
        # Get the executing folder
        self.current_folder = os.path.dirname(pathlib.Path(__file__).resolve())
        if sys.platform == "win32" or sys.platform == "cygwin":
            self.current_folder += "\\"
        else:
            self.current_folder += "/"

        # Cache the env
        self.env_instance = env

        # Get the JSON file(s)
        for file in self.env_instance.project.config['CI_JSON_FILES']:
            # Is this an S3 file? If so, then download it to a temporary file and execute it there
            if (file.startswith("s3://")):
                tmp_file_path = str(self.current_folder) + "tmp_s3_file.json"
                self.copy_s3_file(file, tmp_file_path)
                if (os.path.exists(tmp_file_path)):
                    print("Processing JSON file...")
                    self._process_json_file(tmp_file_path)
                    print("Processed JSON file.")
                    # delete once finished
                    os.remove(tmp_file_path)
                else:
                    sys.exit(f"Cannot parse JSON file: file given [{file}] does not point to a valid file")
            # otherwise it's just a normal file, so execute it
            else:
                if (os.path.exists(file) == False):
                    sys.exit(f"Cannot parse JSON file: file given [{file}] does not point to a valid file")
                print("Processing JSON file...")
                self._process_json_file(file)
                print("Processed JSON file.")
