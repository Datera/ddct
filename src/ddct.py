#!/usr/bin/env python

from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

"""
Datera Deployment Check Tool (DDCT)

Openstack cinder controller level:

Driver check:

Is the latest running?

Auto update?

Is cinder backup setup, if not suggest they get the driver :)


OpenStack Datera types created?

Given the backend name, are types created?


Host level stuff:

Is ARP setup correctly?

#sysctl

#check /etc/sysctl.conf

Settings:

net.ipv4.conf.all.arp_announce = 2

net.ipv4.conf.all.arp_ignore = 1



Is irqbalance running?

#Stop irqbalanace if running

#service irqbalance stop
#Recommend rebalancing IRQ for Network interface based on NIC vendor tools.


Is cpufreq set to performance?

NOTE: this is OS dependent:
https://www.google.com/search?q=linux+cpufreq+howto&oq=linux+cpufreq&aqs=chrome.4.69i57j0l5.6655j0j7&sourceid=chrome&ie=UTF-8,
need Debian / Ubuntu and RedHat / Centos.


Block devices set to NOOP?

Check /sys/block/*/device/scheduler

NOTE:
http://www.techrepublic.com/article/how-to-change-the-linux-io-scheduler-to-fit-your-needs/



Multipath.conf setting and nova.conf check:

#If They want to use Multipath.conf this is needed.

https://drive.google.com/drive/u/1/folders/0B7eQy3YWSJolYnFQYVJnYzc2cWs

Check Page 11 here.  Ideally we could have a reference multipath.conf file
that checks the local multipath.conf file


If this tool can be used out side of OpenStack environments to validate
best practices that would be even better!!
"""

import argparse
import io
import json
import os
import sys


import common
from common import SUCCESS, ff, sf, gen_report
from validators import client_check, connection_check
from check_drivers import check_drivers


CONFIG = {"mgmt_ip": "1.1.1.1",
          "vip1_ip": "10.0.1.1",
          "vip2_ip": "10.0.2.1",
          "username": "admin",
          "password": "password",
          "cinder-volume": {
              "version": "2.7.2",
              "location": None}}

GEN_CONFIG_FILE = "ddct.json"
DEFAULT_CONFIG_FILE = ".ddct.json"


def generate_config_file():
    print("Generating example config file: {}".format(GEN_CONFIG_FILE))
    with io.open(GEN_CONFIG_FILE, "w+") as f:
        try:
            json.dump(CONFIG, f, indent=4, sort_keys=True)
        except TypeError:
            # Python 2 compatibility
            f.write(json.dumps(CONFIG, indent=4, sort_keys=True).decode(
                'utf-8'))
        sys.exit(0)


def main(args):
    # Generate or load config file
    if args.generate_config_file:
        generate_config_file()
        return SUCCESS
    elif args.config_file:
        if not os.path.exists(args.config_file):
            raise EnvironmentError(
                "Config file {} not found".format(args.config_file))
        with io.open(args.config_file, "r") as f:
            config = json.load(f)
    elif os.path.exists(DEFAULT_CONFIG_FILE):
        with io.open(DEFAULT_CONFIG_FILE, "r") as f:
            config = json.load(f)
    else:
        print("No config file found.\nMust either have a {} file in current "
              "directory or manually specify config file via '-c' flag. "
              "\nA sample config file can be generated with the '-g' flag."
              "".format(
                  DEFAULT_CONFIG_FILE))
        return ff("CONFIG", "Missing config file")

    sf("CONFIG")
    client_check(config)
    connection_check(config)
    check_drivers(config)
    gen_report()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--generate-config-file", action="store_true",
                        help="Generate config file example")
    parser.add_argument("-c", "--config-file",
                        help="Config file location")
    args = parser.parse_args()

    common.verbose = args.verbose
    sys.exit(main(args))
