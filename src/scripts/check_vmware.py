#!/usr/bin/env python

from __future__ import print_function

import argparse
import sys
import subprocess

VERBOSE = False


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def exe_esx(cmd):
    cmd = "esxcli {}".format(cmd)
    vprint(cmd)
    return subprocess.check_output(cmd, shell=True)


def main(args):
    # Disable interrupt moderation at a physical NIC driver level
    # This is NIC specific so we should detect the NIC before executing
    exe_esx("esxcli system module parameters set -m ixgbe -p "
            "\"InterruptThrottleRate=0\"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    VERBOSE = args.verbose
    sys.exit(main())
