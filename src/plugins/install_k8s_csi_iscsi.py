from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import sys

from common import exe_check, verbose, vprint

INSTALL_SCRIPT = ("https://raw.githubusercontent.com/Datera/datera-csi/"
                  "master/assets/setup_iscsi.sh")
SCRIPT_NAME = INSTALL_SCRIPT.split('/')[-1]


def get_install_script():
    vprint("Retrieving installation script")
    if not exe_check("wget {}".format(INSTALL_SCRIPT)):
        print("Failed to get iscsi-recv installation script {}".format(
            INSTALL_SCRIPT))
        sys.exit(1)
    if not exe_check("chmod +x {}".format(SCRIPT_NAME)):
        print("Failed to set iscsi-recv install script to executable: {}"
              "".format(SCRIPT_NAME))


def run_install_script():
    with verbose():
        if not exe_check("./{}".format(SCRIPT_NAME)):
            print("Failed to run iscsi-recv install script successfully: {}"
                  "".format(SCRIPT_NAME))


def install(config):
    print("Running K8s CSI ISCSI installer")
    get_install_script()
    run_install_script()
