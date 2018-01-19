#!/usr/bin/env python

from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os
import re
import shutil
import subprocess
import uuid

from common import vprint, exe, exe_check, ff, sf, wf

REQUIREMENTS = ('git', 'curl')
GITHUB = "http://github.com/Datera/cinder-driver"
HOME = os.path.expanduser("~")
REPO = "{}/cinder-driver".format(HOME)
ETC = "/etc/cinder/cinder.conf"
PACKAGE_INSTALL = "/usr/lib/python2.7/dist-packages/cinder"
SITE_PACKAGE_INSTALL = "/usr/lib/python2.7/site-packages/cinder"
DEVSTACK_INSTALL = "/opt/stack/cinder/cinder"

VERSION_RE = re.compile("^\s+VERSION = ['\"]([\d\.]+)['\"]\s*$")

ETC_DEFAULT_RE = re.compile("^\[DEFAULT\]\s*$")
ETC_SECTION_RE = re.compile("^\[[Dd]atera\]\s*$")
ETC_TEMPLATE = """
[datera]
volume_driver = cinder.volume.drivers.datera.datera_iscsi.DateraDriver
san_is_local = True
san_ip = {ip}
san_login = {login}
san_password = {password}
volume_backend_name = datera
datera_debug = True
"""


def check_requirements():
    vprint("Checking Requirements")
    for binary in REQUIREMENTS:
        if not exe_check("which {}".format(binary), err=False):
            print("Missing requirement:", binary)
            print("Please install and retry script")


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


def detect_service_restart_cmd(service, display=False):

    def is_journalctl():
        try:
            exe("journalctl --unit {} | grep 'No entries'")
            return False
        except subprocess.CalledProcessError:
            return True

    def screen_name(service):
        first = service[0]
        pos = service.find("-")
        return "-".join((first, service[pos+1:pos+4]))

    result = exe(
        "sudo service --status-all 2>&1 | awk '{{print $4}}' | grep {} || true"
        "".format(service))
    if service in result:
        return "sudo service {} restart".format(result.strip())
    result = exe("sudo sysctl --all 2>&1 | awk '{{print $1}}' | grep {} || "
                 "true".format(service))
    if service in result:
        return "sudo service {} restart".format(
            result.replace(".service", "").strip())
    sn = screen_name(service)
    result = exe(
        "screen -Q windows | grep {}".format(sn))
    if sn in result:
        if display:
            return "screen -S stack -p {} -X stuff $'\\003 !!\\n'".format(sn)
        else:
            return "screen -S stack -p {} -X stuff $'\003 !!\\n'".format(sn)
    raise EnvironmentError("Service: {} not detected".format(service))


def clone_driver(cinder_driver, d_version):
    check_requirements()
    # Get repository and checkout version
    if not cinder_driver:
        repo = REPO
        if not os.path.isdir("{}/cinder-driver".format(HOME)):
            exe("cd {} && git clone {}".format(HOME, GITHUB))
    else:
        repo = cinder_driver
    version = d_version
    exe("cd {} && git fetch --all".format(HOME))
    exe("cd {} && git checkout {}".format(repo, version))
    loc = detect_cinder_install()
    return repo, loc


def install_volume_driver(cinder_driver, ip, username, password, d_version):
    # Copy files to install location
    repo, loc = clone_driver(cinder_driver, d_version)
    dloc = os.path.join(loc, "volume/drivers")
    exe("cp -r {}/src/datera/ {}".format(repo, dloc))

    # Modify etc file
    data = None
    with io.open(ETC, 'r') as f:
        data = f.readlines()
    # Place lines under [DEFAULT]
    insert = 0
    for index, line in enumerate(data):
        if any((elem in line for elem in
                ("enabled_backends", "verbose", "debug"))):
            del data[index]
        elif "DEFAULT" in line:
            insert = index
    data.insert(insert + 1, "enabled_backends = datera")
    data.insert(insert + 1, "verbose = True")
    data.insert(insert + 1, "debug = True")

    # Write [datera] section
    tdata = ETC_TEMPLATE.format(
        ip=ip,
        login=username,
        password=password)
    data.extend(tdata.splitlines())

    shutil.copyfile(ETC, ETC + ".bak.{}".format(str(uuid.uuid4())[:4]))
    with io.open(ETC, 'w') as f:
        for line in data:
            line = line.strip()
            f.write(line)
            f.write("\n")

    # Restart cinder-volume service
    restart = detect_service_restart_cmd("cinder-volume")
    vprint("Restarting the cinder-volume service")
    if loc == DEVSTACK_INSTALL:
        vprint("Detected devstack")
    else:
        vprint("Detected non-devstack")
    exe(restart)


def check_drivers(config):
    check_cinder_volume_driver(config)


def check_cinder_volume_driver(config):
    if "cinder-volume" not in config:
        return None
    need_version = config["cinder-volume"]["version"].strip("v")
    name = "Cinder Volume"
    loc = detect_cinder_install()
    dfile = os.path.join(loc, "volume/drivers/datera/datera_iscsi.py")
    if not os.path.exists(dfile):
        errloc = os.path.join(loc, "volume/drivers")
        return ff(name, "Couldn't detect Datera Cinder driver install at "
                        "{}".format(errloc))
    version = None
    with io.open(dfile, 'r') as f:
        for line in f:
            version = VERSION_RE.match(line)
            if version:
                version = version.group(1)
                break
    if not version:
        return ff(name, "No version detected for Datera Cinder driver at "
                        "{}".format(dfile))
    if version != need_version:
        return ff(name, "Cinder Driver version mismatch, have: {}, want: "
                        "{}".format(version, need_version))

    section = None
    with io.open(ETC, 'r') as f:
        for line in f:
            default = ETC_DEFAULT_RE.match(line)
            if default:
                break
        if not default:
            ff(name, "[DEFAULT] section missing from "
                     "/etc/cinder/cinder.conf")
        for line in f:
            section = ETC_SECTION_RE.match(line)
            if section:
                break
            if line.startswith("enabled_backends"):
                if "datera" not in line:
                    ff(name, "datera is not set under enabled_backends "
                             "in /etc/cinder/cinder.conf")
            if line.startswith("default_volume_type"):
                if "datera" not in line:
                    wf(name, "datera is not set as default_volume_type in"
                             " /etc/cinder/cinder.conf")

        if not section:
            return ff(name, "[datera] section missing from "
                            "/etc/cinder/cinder.conf")
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

    if not san_check:
        ff(name, "san_ip line is missing or not matching ip address:"
                 " {}".format(ip))
    if not user_check:
        ff(name, "san_login line is missing or not matching username:"
                 " {}".format(user))
    if not pass_check:
        ff(name, "san_password line is missing or not matching "
                 "password: {}".format(passwd))
    if not vbn_check:
        ff(name, "volume_backend_name is not set")
    if not debug_check:
        wf(name, "datera_debug is not enabled")

    sf(name)
