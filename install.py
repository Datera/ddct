#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division

import argparse
import io
import os
import stat
import subprocess
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(DIR, ".ddct")
PYTHON = os.path.join(VENV, "bin", "python")
PIP = os.path.join(VENV, "bin", "pip")
REQUIREMENTS = os.path.join(DIR, "requirements.txt")
DDCT = os.path.join(DIR, "ddct")
DDCTPY = os.path.join(DIR, "src", "ddct.py")
CONFIG = os.path.join(DIR, "datera-config.json")
DDCT_TEMPLATE = """
#!/bin/bash

DSDK_LOG_CFG=disable
{python} {ddct} $@
"""

VERBOSE = False


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def exe(cmd):
    vprint("Running cmd:", cmd)
    return subprocess.check_output(cmd, shell=True)


def exe_pip(cmd):
    vprint("Running pip cmd:", cmd)
    cmd = " ".join((PIP, cmd))
    return subprocess.check_output(cmd, shell=True)


def exe_python(cmd):
    vprint("Running python cmd:", cmd)
    cmd = " ".join((PYTHON, cmd))
    return subprocess.check_output(cmd, shell=True)


def install_packages():
    # Install prereqs Ubuntu
    try:
        exe("sudo apt-get install python-virtualenv python-dev "
            "libffi-dev libssl-dev gcc -y")
    # Install prereqs Centos
    except subprocess.CalledProcessError as e:
        vprint(e)
        print("Ubuntu packages failed, trying RHEL packages")
        try:
            exe("sudo yum install python-virtualenv python-devel "
                "libffi-devel openssl-devel gcc -y")
        except subprocess.CalledProcessError as e:
            vprint(e)
            print("RHEL packages failed, trying SUSE packages")
            try:
                exe("sudo zypper install python-setuptools "
                    "python-devel, libffi-devel opennssl-devel gcc -y")
                exe("sudo easy_install pip")
                exe("sudo pip install virtualenv")
            except subprocess.CalledProcessError as e:
                vprint(e)
                print("SUSE packages failed")
                print("Could not install prereqs")
            return 1


def main(args):
    global VERBOSE
    VERBOSE = args.verbose
    try:
        exe("which virtualenv")
    except subprocess.CalledProcessError:
        if install_packages() == 1:
            return 1
    if not os.path.isdir(VENV):
        try:
            exe("virtualenv {}".format(VENV))
        except subprocess.CalledProcessError:
            # Sometimes this fails because python-setuptools isn't installed
            # this almost always happens on SUSE, but we'll install all
            # necessary packages just to be safe.
            if install_packages() == 1:
                return 1
            exe("virtualenv {}".format(VENV))
    exe_pip("install -U pip")
    exe_pip("install -U -r {}".format(REQUIREMENTS))

    if not os.path.isfile(DDCT):
        # Create ddct executable
        with io.open(DDCT, 'w+') as f:
            f.write(DDCT_TEMPLATE.format(
                python=PYTHON,
                ddct=DDCTPY))
        # Ensure it is executable
        st = os.stat(DDCT)
        os.chmod(DDCT, st.st_mode | stat.S_IEXEC)

    if not os.path.isfile(CONFIG):
        exe("cd {} && {} --gen-config json".format(DIR, DDCT))

    print("DDCT is now installed.  Use '{}' to run DDCT."
          "\nThe generated config file is located at '{}'. "
          "\nIf an existing universal datera config file should be "
          "used, remove the generated config file".format(
              DDCT, CONFIG))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args))
