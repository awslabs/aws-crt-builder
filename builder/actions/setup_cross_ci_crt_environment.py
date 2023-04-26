# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.action import Action
from builder.core.host import current_os, current_arch
import json
import tempfile

import builder.actions.setup_cross_ci_helpers as helpers


class SetupCrossCICrtEnvironment(Action):

    # Needed to keep the temporary files alive
    tmp_file_storage = []

    # NOTE: Either manually set this to 'true' or run the following export:
    # * export setup_cross_crt_ci_environment_local=true
    # This will adjust some environment variables to point to 'host.docker.internal'
    # and will run Codebuild tests even if the Codebuild environment is NOT set.
    is_running_locally = False

    # Will be True if on Windows
    is_windows = False
    # Will be True if on Mac
    is_mac = False
    # Will be True if on Linux (including freebsd and openbsd)
    is_linux = False
    # Will be True if on ARM
    is_arm = False
    # Will be True if on Codebuild
    is_codebuild = False

    def _setenv(self, env, env_name, env_data):
        # Kinda silly to have a function for this, but makes the API calls consistent and looks better
        # beside the other functions...
        print(f"Setting environment variable {env_name}...")
        env.shell.setenv(env_name, str(env_data), quiet=True)

    def _setenv_secret(self, env, env_name, secret_name):
        try:
            environment_value = env.shell.get_secret(str(secret_name))
            self._setenv(env, env_name, environment_value)
        except:
            print("[ERROR]: Could not get secret with name: " + str(secret_name))
            raise ValueError("Exception occurred trying to get secret")

    def _setenv_secret_file(self, env, env_name, secret_name):
        try:
            environment_value = env.shell.get_secret(str(secret_name))
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            # lgtm [py/clear-text-storage-sensitive-data]
            tmp_file.write(str.encode(environment_value))
            tmp_file.flush()
            self.tmp_file_storage.append(tmp_file)
            self._setenv(env, env_name, tmp_file.name)
        except:
            print("[ERROR]: Could not get secret file with name: " + str(secret_name))
            raise ValueError("Exception occurred trying to get secret file")

    def _setenv_role_arn(self, env, env_name, role_arn):
        try:
            cmd = ["aws", "--region", "us-east-1", "sts", "assume-role",
                   "--role-arn", role_arn, "--role-session", "CI_Test_Run"]
            result = env.shell.exec(*cmd, check=True, quiet=True)
            result_json = json.loads(result.output)
            self._setenv(env, env_name + "_ACCESS_KEY", result_json["Credentials"]["AccessKeyId"])
            self._setenv(env, env_name + "_SECRET_ACCESS_KEY", result_json["Credentials"]["SecretAccessKey"])
            self._setenv(env, env_name + "_SESSION_TOKEN", result_json["Credentials"]["SessionToken"])
        except:
            print("[ERROR]: Could not get AWS arn role: " + str(role_arn))
            raise ValueError("Exception occurred trying to get role arn")

    def _setenv_s3(self, env, env_name, s3_file):
        try:
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            tmp_file.flush()
            self.tmp_file_storage.append(tmp_file)
            tmp_s3_filepath = tmp_file.name
            cmd = ['aws', '--region', 'us-east-1', 's3', 'cp',
                   s3_file, tmp_s3_filepath]
            env.shell.exec(*cmd, check=True, quiet=True)
            self._setenv(env, env_name, tmp_s3_filepath)
        except:
            print("[ERROR]: Could not get S3 file: " + str(s3_file))
            raise ValueError("Exception occurred trying to get S3 file")

    def _common_setup(self, env):

        ################################################
        # NON-MQTT / GENERAL ENVIRONMENT VARIABLES
        ################################################

        self._setenv(env, "AWS_TEST_IS_CI", True)

        ################################################
        # MQTT5 IOT CORE CREDENTIALS
        ################################################

        # COMMON/FREQUENTLY USED (endpoint, mTLS with key and cert, etc.)
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_HOST", "unit-test/endpoint")
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_REGION", "us-east-1")
        self._setenv_secret_file(env, "AWS_TEST_MQTT5_IOT_CORE_RSA_CERT", "ci/mqtt5/us/Mqtt5Prod/cert")
        self._setenv_secret_file(env, "AWS_TEST_MQTT5_IOT_CORE_RSA_KEY", "ci/mqtt5/us/Mqtt5Prod/key")
        self._setenv_role_arn(env, "AWS_TEST_MQTT5_ROLE_CREDENTIAL",
                              "arn:aws:iam::123124136734:role/assume_role_connect_iot")

        # CUSTOM KEY OPS
        if (self.is_linux == True):
            self._setenv_secret_file(env, "AWS_TEST_MQTT5_CUSTOM_KEY_OPS_CERT", "unit-test/certificate")
            self._setenv_secret_file(env, "AWS_TEST_MQTT5_CUSTOM_KEY_OPS_KEY", "unit-test/privatekey-p8")
            pass

        # Cognito
        self._setenv(env, "AWS_TEST_MQTT5_COGNITO_ENDPOINT", "cognito-identity.us-east-1.amazonaws.com")
        self._setenv_secret(env, "AWS_TEST_MQTT5_COGNITO_IDENTITY", "aws-c-auth-testing/cognito-identity")

        # UNSIGNED CUSTOM AUTH
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_NO_SIGNING_AUTHORIZER_NAME",
                            "ci/mqtt5/us/authorizer/unsigned/name")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_NO_SIGNING_AUTHORIZER_USERNAME",
                            "ci/mqtt5/us/authorizer/unsigned/username")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_NO_SIGNING_AUTHORIZER_PASSWORD",
                            "ci/mqtt5/us/authorizer/unsigned/password")

        # SIGNED CUSTOM AUTH
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_SIGNING_AUTHORIZER_NAME",
                            "ci/mqtt5/us/authorizer/signed/name")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_SIGNING_AUTHORIZER_USERNAME",
                            "ci/mqtt5/us/authorizer/signed/username")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_SIGNING_AUTHORIZER_PASSWORD",
                            "ci/mqtt5/us/authorizer/signed/password")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_SIGNING_AUTHORIZER_TOKEN",
                            "ci/mqtt5/us/authorizer/signed/tokenvalue")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_SIGNING_AUTHORIZER_TOKEN_KEY_NAME",
                            "ci/mqtt5/us/authorizer/signed/tokenkeyname")
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_SIGNING_AUTHORIZER_TOKEN_SIGNATURE",
                            "ci/mqtt5/us/authorizer/signed/signature")

        # JAVA KEYSTORE
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_KEYSTORE_FORMAT", "JKS")
        self._setenv_s3(env, "AWS_TEST_MQTT5_IOT_CORE_KEYSTORE_FILE",
                        "s3://aws-crt-test-stuff/unit-test-keystore.keystore")
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_KEYSTORE_PASSWORD", "PKCS12_KEY_PASSWORD")
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_KEYSTORE_CERT_ALIAS", "PKCS12_ALIAS")
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_KEYSTORE_CERT_PASSWORD", "PKCS12_KEY_PASSWORD")

        # PKCS12
        if (self.is_mac == True):
            self._setenv_s3(env, "AWS_TEST_MQTT5_IOT_CORE_PKCS12_KEY",
                            "s3://aws-crt-test-stuff/unit-test-key-pkcs12.pem")
            self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_PKCS12_KEY_PASSWORD", "PKCS12_KEY_PASSWORD")

        # Windows Key Cert
        if (self.is_windows == True):
            self._setenv_s3(env, "AWS_TEST_MQTT5_IOT_CORE_WINDOWS_PFX_CERT_NO_PASS",
                            "s3://aws-crt-test-stuff/unit-test-pfx-no-password.pfx")
            helper.create_windows_cert_store(
                env, "AWS_TEST_MQTT5_IOT_CORE_WINDOWS_PFX_CERT_NO_PASS", "AWS_TEST_MQTT5_IOT_CORE_WINDOWS_CERT_STORE")

        # X509
        self._setenv_secret(env, "AWS_TEST_MQTT5_IOT_CORE_X509_ENDPOINT", "ci/mqtt5/us/x509/endpoint")
        self._setenv_secret_file(env, "AWS_TEST_MQTT5_IOT_CORE_X509_CA", "X509IntegrationTestRootCA")
        self._setenv_secret_file(env, "AWS_TEST_MQTT5_IOT_CORE_X509_KEY", "X509IntegrationTestPrivateKey")
        self._setenv_secret_file(env, "AWS_TEST_MQTT5_IOT_CORE_X509_CERT", "X509IntegrationTestCertificate")
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_X509_ROLE_ALIAS", "X509IntegrationTestRoleAlias")
        self._setenv(env, "AWS_TEST_MQTT5_IOT_CORE_X509_THING_NAME", "X509IntegrationTestThing")

        ################################################
        # MQTT311 IOT CORE CREDENTIALS
        ################################################

        # COMMON/FREQUENTLY USED (endpoint, mTLS with key and cert, etc.)
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_HOST", "unit-test/endpoint")
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_REGION", "us-east-1")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_RSA_CERT", "ci/mqtt5/us/Mqtt5Prod/cert")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_RSA_KEY", "ci/mqtt5/us/Mqtt5Prod/key")
        self._setenv_role_arn(env, "AWS_TEST_MQTT311_ROLE_CREDENTIAL",
                              "arn:aws:iam::123124136734:role/assume_role_connect_iot")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_ECC_KEY", "ecc-test/certificate")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_ECC_CERT", "ecc-test/privatekey")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_ROOT_CA", "unit-test/rootca")

        # Cognito
        self._setenv(env, "AWS_TEST_MQTT311_COGNITO_ENDPOINT", "cognito-identity.us-east-1.amazonaws.com")
        self._setenv_secret(env, "AWS_TEST_MQTT311_COGNITO_IDENTITY", "aws-c-auth-testing/cognito-identity")

        # CUSTOM KEY OPS
        if (self.is_linux == True):
            self._setenv_secret_file(env, "AWS_TEST_MQTT311_CUSTOM_KEY_OPS_CERT", "unit-test/certificate")
            self._setenv_secret_file(env, "AWS_TEST_MQTT311_CUSTOM_KEY_OPS_KEY", "unit-test/privatekey-p8")
            pass

        # UNSIGNED CUSTOM AUTH
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_NO_SIGNING_AUTHORIZER_NAME",
                            "ci/mqtt5/us/authorizer/unsigned/name")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_NO_SIGNING_AUTHORIZER_USERNAME",
                            "ci/mqtt5/us/authorizer/unsigned/username")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_NO_SIGNING_AUTHORIZER_PASSWORD",
                            "ci/mqtt5/us/authorizer/unsigned/password")

        # SIGNED CUSTOM AUTH
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_SIGNING_AUTHORIZER_NAME",
                            "ci/mqtt5/us/authorizer/signed/name")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_SIGNING_AUTHORIZER_USERNAME",
                            "ci/mqtt5/us/authorizer/signed/username")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_SIGNING_AUTHORIZER_PASSWORD",
                            "ci/mqtt5/us/authorizer/signed/password")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_SIGNING_AUTHORIZER_TOKEN",
                            "ci/mqtt5/us/authorizer/signed/tokenvalue")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_SIGNING_AUTHORIZER_TOKEN_KEY_NAME",
                            "ci/mqtt5/us/authorizer/signed/tokenkeyname")
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_SIGNING_AUTHORIZER_TOKEN_SIGNATURE",
                            "ci/mqtt5/us/authorizer/signed/signature")

        # JAVA KEYSTORE
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_KEYSTORE_FORMAT", "JKS")
        self._setenv_s3(env, "AWS_TEST_MQTT311_IOT_CORE_KEYSTORE_FILE",
                        "s3://aws-crt-test-stuff/unit-test-keystore.keystore")
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_KEYSTORE_PASSWORD", "PKCS12_KEY_PASSWORD")
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_KEYSTORE_CERT_ALIAS", "PKCS12_ALIAS")
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_KEYSTORE_CERT_PASSWORD", "PKCS12_KEY_PASSWORD")

        # PKCS12
        if (self.is_mac == True):
            self._setenv_s3(env, "AWS_TEST_MQTT311_IOT_CORE_PKCS12_KEY",
                            "s3://aws-crt-test-stuff/unit-test-key-pkcs12.pem")
            self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_PKCS12_KEY_PASSWORD", "PKCS12_KEY_PASSWORD")

        # Windows Key Cert
        if (self.is_windows == True):
            self._setenv_s3(env, "AWS_TEST_MQTT311_IOT_CORE_WINDOWS_PFX_CERT_NO_PASS",
                            "s3://aws-crt-test-stuff/unit-test-pfx-no-password.pfx")
            helper.create_windows_cert_store(
                env, "AWS_TEST_MQTT311_IOT_CORE_WINDOWS_PFX_CERT_NO_PASS", "AWS_TEST_MQTT311_IOT_CORE_WINDOWS_CERT_STORE")

        # X509
        self._setenv_secret(env, "AWS_TEST_MQTT311_IOT_CORE_X509_ENDPOINT", "ci/mqtt5/us/x509/endpoint")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_X509_CA", "X509IntegrationTestRootCA")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_X509_KEY", "X509IntegrationTestPrivateKey")
        self._setenv_secret_file(env, "AWS_TEST_MQTT311_IOT_CORE_X509_CERT", "X509IntegrationTestCertificate")
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_X509_ROLE_ALIAS", "X509IntegrationTestRoleAlias")
        self._setenv(env, "AWS_TEST_MQTT311_IOT_CORE_X509_THING_NAME", "X509IntegrationTestThing")

        ################################################
        # MOSQUITTO / CODEBUILD ONLY
        ################################################

        # The Mosquitto direct MQTT host endpoint used in CI on Codebuild.

        if (self.is_codebuild == True):

            ########## MQTT311 ##########
            self._setenv_secret(env, "AWS_TEST_MQTT311_DIRECT_MQTT_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT311_DIRECT_MQTT_PORT", "1883")
            self._setenv_secret(env, "AWS_TEST_MQTT311_DIRECT_MQTT_BASIC_AUTH_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT311_DIRECT_MQTT_BASIC_AUTH_PORT", "1884")
            self._setenv_secret(env, "AWS_TEST_MQTT311_DIRECT_MQTT_TLS_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT311_DIRECT_MQTT_TLS_PORT", "8883")
            self._setenv_secret_file(env, "AWS_TEST_MQTT311_CERTIFICATE_FILE", "ci/mqtt5/us/Mqtt5Prod/cert")
            self._setenv_secret_file(env, "AWS_TEST_MQTT311_KEY_FILE", "ci/mqtt5/us/Mqtt5Prod/key")
            self._setenv_secret(env, "AWS_TEST_MQTT311_WS_MQTT_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT311_WS_MQTT_PORT", "8080")
            self._setenv_secret(env, "AWS_TEST_MQTT311_WS_MQTT_BASIC_AUTH_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT311_WS_MQTT_BASIC_AUTH_PORT", "8090")
            self._setenv_secret(env, "AWS_TEST_MQTT311_WS_MQTT_TLS_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT311_WS_MQTT_TLS_PORT", "8081")
            self._setenv(env, "AWS_TEST_MQTT311_BASIC_AUTH_USERNAME", "rw")
            self._setenv(env, "AWS_TEST_MQTT311_BASIC_AUTH_PASSWORD", "rw")
            self._setenv_secret(env, "AWS_TEST_MQTT311_PROXY_HOST", "ci/mqtt5/us/proxy/host")
            self._setenv(env, "AWS_TEST_MQTT311_PROXY_PORT", "3128")

            ########## MQTT5 ##########
            self._setenv_secret(env, "AWS_TEST_MQTT5_DIRECT_MQTT_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT5_DIRECT_MQTT_PORT", "1883")
            self._setenv_secret(env, "AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_PORT", "1884")
            self._setenv_secret(env, "AWS_TEST_MQTT5_DIRECT_MQTT_TLS_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT5_DIRECT_MQTT_TLS_PORT", "8883")
            self._setenv_secret_file(env, "AWS_TEST_MQTT5_CERTIFICATE_FILE", "ci/mqtt5/us/Mqtt5Prod/cert")
            self._setenv_secret_file(env, "AWS_TEST_MQTT5_KEY_FILE", "ci/mqtt5/us/Mqtt5Prod/key")
            self._setenv_secret(env, "AWS_TEST_MQTT5_WS_MQTT_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT5_WS_MQTT_PORT", "8080")
            self._setenv_secret(env, "AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_PORT", "8090")
            self._setenv_secret(env, "AWS_TEST_MQTT5_WS_MQTT_TLS_HOST", "ci/mqtt5/us/mosquitto/host")
            self._setenv(env, "AWS_TEST_MQTT5_WS_MQTT_TLS_PORT", "8081")
            self._setenv(env, "AWS_TEST_MQTT5_BASIC_AUTH_USERNAME", "rw")
            self._setenv(env, "AWS_TEST_MQTT5_BASIC_AUTH_PASSWORD", "rw")
            self._setenv_secret(env, "AWS_TEST_MQTT5_PROXY_HOST", "ci/mqtt5/us/proxy/host")
            self._setenv(env, "AWS_TEST_MQTT5_PROXY_PORT", "3128")

            # If running locally, override the endpoints to localhost on docker ('host.docker.internal')
            if (self.is_running_locally == True):
                self._setenv(env, "AWS_TEST_MQTT311_DIRECT_MQTT_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT311_DIRECT_MQTT_BASIC_AUTH_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT311_DIRECT_MQTT_TLS_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT311_WS_MQTT_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT311_WS_MQTT_BASIC_AUTH_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT311_WS_MQTT_TLS_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT311_PROXY_HOST", "host.docker.internal")

                self._setenv(env, "AWS_TEST_MQTT5_DIRECT_MQTT_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT5_DIRECT_MQTT_TLS_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT5_WS_MQTT_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT5_WS_MQTT_TLS_HOST", "host.docker.internal")
                self._setenv(env, "AWS_TEST_MQTT5_PROXY_HOST", "host.docker.internal")

            ########## HTTP Proxy ##########
            # Never run the HTTP proxy stuff locally for now
            if (self.is_running_locally == False):
                self._setenv_secret("AWS_TEST_HTTP_PROXY_HOST", "ci/http/proxy/host")
                self._setenv("AWS_TEST_HTTP_PROXY_PORT", "3128")
                self._setenv_secret("AWS_TEST_HTTP_PROXY_URL", "ci/http/proxy/url")
                self._setenv_secret("AWS_TEST_HTTPS_PROXY_HOST", "ci/https/proxy/host")
                self._setenv("AWS_TEST_HTTPS_PROXY_PORT", "3128")
                self._setenv_secret("AWS_TEST_HTTPS_PROXY_URL", "ci/https/proxy/url")
                self._setenv_secret("AWS_TEST_HTTP_PROXY_BASIC_HOST", "ci/http/proxy/basichost")
                self._setenv("AWS_TEST_HTTP_PROXY_BASIC_PORT", "3128")
                self._setenv_secret("AWS_TEST_BASIC_AUTH_USERNAME", "ci/http/proxy/username")
                self._setenv_secret("AWS_TEST_BASIC_AUTH_PASSWORD", "ci/http/proxy/password")
                self._setenv_secret("AWS_TEST_HTTP_PROXY_BASIC_URL", "ci/http/proxy/basicurl")

        ################################################
        # POST-PROCESSING
        ################################################
        if (self.is_linux == True and self.is_arm == False):
            self._setenv_secret_file(env, "AWS_TEST_PKCS11_KEY", "unit-test/privatekey-p8")
            self._setenv_secret_file(env, "AWS_TEST_PKCS11_CERTIFICATE", "unit-test/certificate")
            self._setenv_secret_file(env, "AWS_TEST_PKCS11_ROOT_CA", "unit-test/rootca")
            helpers.create_pkcs11_environment(
                env,
                env.shell.getenv("AWS_TEST_PKCS11_KEY"),
                env.shell.getenv("AWS_TEST_PKCS11_CERTIFICATE"),
                env.shell.getenv("AWS_TEST_PKCS11_ROOT_CA"))

        pass

    def run(self, env):
        # Any easier way to use in docker without having to always modify the builder action
        if (env.shell.getenv("setup_cross_crt_ci_environment_local") != None):
            if (env.shell.getenv("setup_cross_crt_ci_environment_local") == "true"):
                self.is_running_locally = True

        our_os = current_os()
        if (our_os == "windows"):
            self.is_windows = True
        elif (our_os == "mac"):
            self.is_mac = True
        elif (our_os == "linux" or our_os == "freebsd" or our_os == "openbsd"):
            self.is_linux = True
        our_arch = current_arch()
        if (our_arch != "x64" and our_arch != "x86"):
            self.is_arm = True

        if (self.is_running_locally == True):
            self.is_codebuild = True
        elif (env.shell.getenv("CODEBUILD_BUILD_ID") != None):
            # List of Codebuild environment variables:
            # https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-env-vars.html
            self.is_codebuild = True

        self._common_setup(env)
