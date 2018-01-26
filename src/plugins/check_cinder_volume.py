from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os
import re
import subprocess

import requests

from common import vprint, exe, ff, wf, check

ETC = "/etc/cinder/cinder.conf"
PACKAGE_INSTALL = "/usr/lib/python2.7/dist-packages/cinder"
SITE_PACKAGE_INSTALL = "/usr/lib/python2.7/site-packages/cinder"
DEVSTACK_INSTALL = "/opt/stack/cinder/cinder"
TAGS = "https://api.github.com/repos/Datera/cinder-driver/tags"
TAG_RE = re.compile("\d+\.\d+\.\d+")

VERSION_RE = re.compile("^\s+VERSION = ['\"]([\d\.]+)['\"]\s*$")

ETC_DEFAULT_RE = re.compile("^\[DEFAULT\]\s*$")
ETC_SECTION_RE = re.compile("^\[[Dd]atera\]\s*$")


def detect_cinder_install():
    if os.path.isdir(PACKAGE_INSTALL):
        return PACKAGE_INSTALL
    elif os.path.isdir(DEVSTACK_INSTALL):
        return DEVSTACK_INSTALL
    elif os.path.isdir(SITE_PACKAGE_INSTALL):
        return SITE_PACKAGE_INSTALL
    else:
        result = None
        try:
            vprint("Normal cinder install not found, searching for driver")
            result = exe("sudo find / -name datera_iscsi.py")
            if not result or result.isspace():
                raise ValueError()
            return result.strip().replace(
                "/volume/drivers/datera/datera_iscsi.py", "")
        except (subprocess.CalledProcessError, ValueError):
            raise EnvironmentError(
                "Cinder installation not found. Usual locations: [{}, {}]"
                "".format(PACKAGE_INSTALL, DEVSTACK_INSTALL))


def get_latest_driver_version():
    found = []
    weighted_found = []
    tags = requests.get(TAGS).json()
    for tag in tags:
        tag = tag['name'].strip("v")
        if TAG_RE.match(tag):
            found.append(tag)
    for f in found:
        # Major, minor, patch
        M, m, p = f.split(".")
        value = int(M) * 10000 + int(m) * 100 + int(p)
        weighted_found.append((value, "v" + f))
    return sorted(weighted_found)[-1][1]


@check("Cinder Volume")
def check_cinder_volume_driver(config):
    version = get_latest_driver_version()
    need_version = version.strip("v")
    loc = detect_cinder_install()
    dfile = os.path.join(loc, "volume/drivers/datera/datera_iscsi.py")
    if not os.path.exists(dfile):
        errloc = os.path.join(loc, "volume/drivers")
        return ff("Couldn't detect Datera Cinder driver install at "
                  "{}".format(errloc), "680E61DB")
    version = None
    with io.open(dfile, 'r') as f:
        for line in f:
            version = VERSION_RE.match(line)
            if version:
                version = version.group(1)
                break
    if not version:
        return ff("No version detected for Datera Cinder driver at "
                  "{}".format(dfile), "A37FD778")
    if version != need_version:
        return ff("Cinder Driver version mismatch, have: {}, want: "
                  "{}".format(version, need_version), "5B6EFC71")

    section = None
    with io.open(ETC, 'r') as f:
        for line in f:
            default = ETC_DEFAULT_RE.match(line)
            if default:
                break
        if not default:
            ff("[DEFAULT] section missing from /etc/cinder/cinder.conf",
               "7B98CFA1")
        for line in f:
            section = ETC_SECTION_RE.match(line)
            if section:
                break
            if line.startswith("enabled_backends"):
                if "datera" not in line:
                    ff("datera is not set under enabled_backends "
                       "in /etc/cinder/cinder.conf", "A4402034")
            if line.startswith("default_volume_type"):
                if "datera" not in line:
                    wf("datera is not set as default_volume_type in"
                       " /etc/cinder/cinder.conf", "C2B8C696")

        if not section:
            return ff("[datera] section missing from "
                      "/etc/cinder/cinder.conf", "525BAAB0")
        dsection = []
        section_match = re.compile("^\[.*\]")
        for line in f:
            if section_match.match(line):
                break
            dsection.append(line)

    san_check = False
    user_check = False
    pass_check = False
    vbn_check = False
    debug_check = False
    defaults_check = False

    ip = config['mgmt_ip']
    user = config['username']
    passwd = config['password']

    for line in dsection:
        if 'san_ip' in line and ip in line:
            san_check = True
        if 'san_login' in line and user in line:
            user_check = True
        if 'san_password' in line and passwd in line:
            pass_check = True
        if 'volume_backend_name' in line and 'datera' in line:
            vbn_check = True
        if 'datera_debug' in line and 'True' in line:
            debug_check = True
        if 'datera_volume_type_defaults' in line:
            defaults_check = True

    if not san_check:
        ff("san_ip line is missing or not matching ip address:"
           " {}".format(ip), "8208B9E7")
    if not user_check:
        ff("san_login line is missing or not matching username:"
           " {}".format(user), "3A6A78D1")
    if not pass_check:
        ff("san_password line is missing or not matching "
           "password: {}".format(passwd), "8DBC87E8")
    if not vbn_check:
        ff("volume_backend_name is not set", "5FEC0454")
    if not debug_check:
        wf("datera_debug is not enabled")
    if not defaults_check:
        wf("datera_volume_type_defaults is not set, consider setting "
           "minimum QoS values here", "B5D29621")


def run_checks(config):
    check_cinder_volume_driver(config)
