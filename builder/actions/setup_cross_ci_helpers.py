"""
Helper functions for setting up CI that is not necessarily environment variable related.
"""

from builder.actions.install import InstallPackages
import re
import os

################################################################################
# Windows Certificate Store


def create_windows_cert_store(env, certificate_env, location_env):
    windows_certificate_location = "CurrentUser\\My"
    windows_certificate_folder = "Cert:\\" + windows_certificate_location

    # Is the environment variable set?
    if (env.shell.getenv(certificate_env) == None):
        print(f"Windows Cert Setup: {certificate_env} not set. Skipping...")
        return
    pfx_cert_path = env.shell.getenv(certificate_env)

    # Import the PFX into the Windows Certificate Store
    # (Passing '$mypwd' is required even though it is empty and our certificate has no password. It fails CI otherwise)
    import_pfx_arguments = [
        "Import-PfxCertificate",
        "-FilePath", pfx_cert_path,
        "-CertStoreLocation", windows_certificate_folder]
    import_result = env.shell.exec("powershell.exe", import_pfx_arguments, check=True)

    # Get the certificate thumbprint from the output:
    import_pfx_output = str(import_result.output)
    # We know the Thumbprint will always be 40 characters long, so we can find it using that
    # TODO: Extract this using a better, more fool-proof method
    thumbprint = ""
    current_str = ""
    # The input comes as a string with some special characters still included, so we need to remove them!
    import_pfx_output = import_pfx_output.replace("\\r", " ")
    import_pfx_output = import_pfx_output.replace("\\n", "\n")
    for i in range(0, len(import_pfx_output)):
        if (import_pfx_output[i] == " " or import_pfx_output[i] == "\n"):
            if (len(current_str) == 40):
                thumbprint = current_str
                break
            current_str = ""
        else:
            current_str += import_pfx_output[i]
    if (thumbprint == ""):
        print(f"Windows Cert Setup: {certificate_env} - ERROR - could not find certificate thumbprint")
        return
    env.shell.setenv(location_env, windows_certificate_location + "\\" + thumbprint)

################################################################################
# PKCS11


def create_pkcs11_environment(env, pkcs8key, pkcs8cert, ca_file):
    # try to install softhsm
    try:
        softhsm_install_acion = InstallPackages(['softhsm'])
        softhsm_install_acion.run(env)
    except:
        print("WARNING: softhsm could not be installed. PKCS#11 tests are disabled")
        return

    softhsm_lib = _find_softhsm_lib()
    if softhsm_lib is None:
        print("WARNING: libsofthsm2.so not found. PKCS#11 tests are disabled")
        return

    # put SoftHSM config file and token directory under the build dir.
    softhsm2_dir = os.path.join(env.build_dir, 'softhsm2')
    conf_path = os.path.join(softhsm2_dir, 'softhsm2.conf')
    token_dir = os.path.join(softhsm2_dir, 'tokens')
    env.shell.mkdir(token_dir)
    _setenv(env, 'SOFTHSM2_CONF', conf_path)
    with open(conf_path, 'w') as conf_file:
        conf_file.write(f"directories.tokendir = {token_dir}\n")

    # print SoftHSM version
    _exec_softhsm2_util(env, '--version')

    # create a token
    _exec_softhsm2_util(
        env,
        '--init-token',
        '--free',  # use any free slot
        '--label', 'my-test-token',
        '--pin', '0000',
        '--so-pin', '0000')

    # we need to figure out which slot the new token is in because:
    # 1) old versions of softhsm2-util make you pass --slot <number>
    #    (instead of accepting --token <name> like newer versions)
    # 2) newer versions of softhsm2-util reassign new tokens to crazy
    #    slot numbers (instead of simply using 0 like older versions)
    slot = _get_token_slots(env)[0]

    # add private key to token
    _exec_softhsm2_util(
        env,
        '--import', pkcs8key,
        '--slot', str(slot),
        '--label', 'my-test-key',
        '--id', 'BEEFCAFE',  # ID is hex
        '--pin', '0000')

    # for logging's sake, print the new state of things
    _exec_softhsm2_util(env, '--show-slots', '--pin', '0000')

    # set env vars for tests
    _setenv(env, 'AWS_TEST_PKCS11_LIB', softhsm_lib)
    _setenv(env, 'AWS_TEST_PKCS11_TOKEN_LABEL', 'my-test-token')
    _setenv(env, 'AWS_TEST_PKCS11_PIN', '0000')
    _setenv(env, 'AWS_TEST_PKCS11_PKEY_LABEL', 'my-test-key')
    _setenv(env, 'AWS_TEST_PKCS11_CERT_FILE', pkcs8cert)
    _setenv(env, 'AWS_TEST_PKCS11_CA_FILE', ca_file)

    # Make usable, 'real' PKCS11 token and key for connection tests
    # MQTT311
    _make_iot_pkcs11_environment_variables(
        env,
        softhsm_lib,
        "AWS_TEST_MQTT311_IOT_CORE_RSA_CERT",
        "AWS_TEST_MQTT311_IOT_CORE_RSA_Key",
        "AWS_TEST_MQTT311_IOT_CORE_PKCS11_LIB",
        "AWS_TEST_MQTT311_IOT_CORE_PKCS11_TOKEN_LABEL",
        "AWS_TEST_MQTT311_IOT_CORE_PKCS11_PIN",
        "AWS_TEST_MQTT311_IOT_CORE_PKCS11_PKEY_LABEL",
        "AWS_TEST_MQTT311_IOT_CORE_PKCS11_CERT_FILE")
    # MQTT5
    _make_iot_pkcs11_environment_variables(
        env,
        softhsm_lib,
        "AWS_TEST_MQTT5_IOT_CORE_RSA_CERT",
        "AWS_TEST_MQTT5_IOT_CORE_RSA_Key",
        "AWS_TEST_MQTT5_IOT_CORE_PKCS11_LIB",
        "AWS_TEST_MQTT5_IOT_CORE_PKCS11_TOKEN_LABEL",
        "AWS_TEST_MQTT5_IOT_CORE_PKCS11_PIN",
        "AWS_TEST_MQTT5_IOT_CORE_PKCS11_PKEY_LABEL",
        "AWS_TEST_MQTT5_IOT_CORE_PKCS11_CERT_FILE")


def _setenv(env, var, value):
    """
    Set environment variable now,
    and ensure the environment variable is set again when tests run
    """
    env.shell.setenv(var, value)
    env.project.config['test_env'][var] = value


def _make_iot_pkcs11_environment_variables(
        env, softhsm_lib, env_cert, env_key, env_pkcs11_lib, env_pkcs11_token, env_pkcs11_pin,
        env_pkcs11_private_label, env_pkcs11_cert):

    if (env.shell.getenv(env_cert) != None and
            env.shell.getenv(env_key) != None):

        # create a token
        _exec_softhsm2_util(
            env,
            '--init-token',
            '--free',  # use any free slot
            '--label', 'my-test-iot-token',
            '--pin', '0000',
            '--so-pin', '0000')

        # we need to figure out which slot the new token is in because:
        # 1) old versions of softhsm2-util make you pass --slot <number>
        #    (instead of accepting --token <name> like newer versions)
        # 2) newer versions of softhsm2-util reassign new tokens to crazy
        #    slot numbers (instead of simply using 0 like older versions)
        iot_slot = _get_token_slots()[0]

        # add private key to token
        _exec_softhsm2_util(
            env,
            '--import', env.shell.getenv(env_key),
            '--slot', str(iot_slot),
            '--label', 'my-test-iot-key',
            '--id', 'BEEFCAFF',  # ID is hex
            '--pin', '0000')

        # for logging's sake, print the new state of things
        _exec_softhsm2_util(env, '--show-slots', '--pin', '0000')

        # set env vars for tests
        _setenv(env, env_pkcs11_lib, softhsm_lib)
        _setenv(env, env_pkcs11_token, 'my-test-iot-token')
        _setenv(env, env_pkcs11_pin, '0000')
        _setenv(env, env_pkcs11_private_label, 'my-test-iot-key')
        _setenv(env, env_pkcs11_cert, env.shell.getenv(env_cert))


def _find_softhsm_lib():
    """Return path to SoftHSM2 shared lib, or None if not found"""

    # note: not using `ldconfig --print-cache` to find it because
    # some installers put it in weird places where ldconfig doesn't look
    # (like in a subfolder under lib/)

    for lib_dir in ['lib64', 'lib']:  # search lib64 before lib
        for base_dir in ['/usr/local', '/usr', '/', ]:
            search_dir = os.path.join(base_dir, lib_dir)
            for root, dirs, files in os.walk(search_dir):
                for file_name in files:
                    if 'libsofthsm2.so' in file_name:
                        return os.path.join(root, file_name)
    return None


def _exec_softhsm2_util(env, *args, **kwargs):
    if not 'check' in kwargs:
        kwargs['check'] = True

    result = env.shell.exec('softhsm2-util', *args, **kwargs)

    # older versions of softhsm2-util (2.1.0 is a known offender)
    # return error code 0 and print the help if invalid args are passed.
    # This should be an error.
    #
    # invalid args can happen because newer versions of softhsm2-util
    # support more args than older versions, so what works on your
    # machine might not work on some ancient docker image.
    if 'Usage: softhsm2-util' in result.output:
        raise Exception('softhsm2-util failed')

    return result


def _get_token_slots(env):
    """Return array of IDs for slots with initialized tokens"""
    token_slot_ids = []

    output = _exec_softhsm2_util(env, '--show-slots', quiet=True).output

    # --- output looks like ---
    # Available slots:
    # Slot 0
    #    Slot info:
    #        ...
    #        Token present:    yes
    #    Token info:
    #        ...
    #        Initialized:      yes
    current_slot = None
    current_info_block = None
    for line in output.splitlines():
        # check for start of "Slot <ID>" block
        m = re.match(r"Slot ([0-9]+)", line)
        if m:
            current_slot = int(m.group(1))
            current_info_block = None
            continue

        if current_slot is None:
            continue

        # check for start of next indented block, like "Token info"
        m = re.match(r"    ([^ ].*)", line)
        if m:
            current_info_block = m.group(1)
            continue

        if current_info_block is None:
            continue

        # if we're in token block, check for "Initialized: yes"
        if "Token info" in current_info_block:
            if re.match(r" *Initialized: *yes", line):
                token_slot_ids.append(current_slot)

    return token_slot_ids

################################################################################
