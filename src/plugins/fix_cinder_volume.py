from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os
import shutil
import uuid

from common import vprint, exe, exe_check
from fixers import no_fix
from plugins.check_cinder_volume import ETC, detect_cinder_install

REQUIREMENTS = ('git', 'curl')
DEVSTACK_INSTALL = "/opt/stack/cinder/cinder"
GITHUB = "http://github.com/Datera/cinder-driver"
HOME = os.path.expanduser("~")
REPO = "{}/cinder-driver".format(HOME)
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


def detect_service_restart_cmd(service, display=False):

    def is_journalctl():
        return exe_check("journalctl --unit {} | grep 'No entries'", err=False)

    def screen_name(service):
        first = service[0]
        pos = service.find("-")
        return "-".join((first, service[pos+1:pos+4]))

    result = exe(
        "service --status-all 2>&1 | awk '{{print $4}}' | grep {} || true"
        "".format(service))
    if service in result:
        return "service {} restart".format(result.strip())
    result = exe("sysctl --all 2>&1 | awk '{{print $1}}' | grep {} || "
                 "true".format(service))
    if service in result:
        return "service {} restart".format(
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
    """Installs Cinder volume driver"""
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


def load_fixes():
    return {
        "680E61DB": [no_fix],
        "A37FD778": [no_fix],
        "5B6EFC71": [no_fix],
        "A4402034": [no_fix]}
