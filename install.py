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
CONFIG = os.path.join(DIR, "ddct.json")
DDCT_TEMPLATE = """
#!/bin/bash

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


def main(args):
    global VERBOSE
    VERBOSE = args.verbose
    try:
        exe("which virtualenv")
    except subprocess.CalledProcessError:
        # Install prereqs Ubuntu
        try:
            exe("sudo apt-get install python-virtualenv python-dev "
                "libffi-dev libssl-dev -y")
        # Install prereqs Centos
        except subprocess.CalledProcessError as e:
            vprint(e)
            try:
                exe("sudo yum install python-virtualenv python-devel "
                    "libffi-devel openssl-devel -y")
            except subprocess.CalledProcessError as e:
                print(e)
                print("Could not install prereqs")
                return 1
    if not os.path.isdir(VENV):
        exe("virtualenv {}".format(VENV))
        exe_pip("install -r {}".format(REQUIREMENTS))

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
        exe("cd {} && {} -g".format(DIR, DDCT))

    print("DDCT is now installed.  Use '{}' to run DDCT."
          "\nThe generated config file is located at '{}'".format(
              DDCT, CONFIG))
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args))
