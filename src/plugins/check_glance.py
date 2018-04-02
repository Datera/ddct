from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os
import re
import subprocess

from common import vprint, exe, ff, wf, check, get_latest_driver_version

ETC = "/etc/glance/glance-api.conf"
PACKAGE_INSTALL = "/usr/lib/python2.7/dist-packages/glance_store"
PACKAGE_INSTALL_2 = "/usr/local/lib/python2.7/dist-packages/glance_store"
SITE_PACKAGE_INSTALL = "/usr/lib/python2.7/site-packages/glance_store"
SITE_PACKAGE_INSTALL_2 = "/usr/local/lib/python2.7/site-packages/glance_store"
DEVSTACK_INSTALL = "/usr/local/lib/python2.7/site-packages/glance_store"
TAGS = "https://api.github.com/repos/Datera/glance-driver/tags"

VERSION_RE = re.compile("^\s+VERSION = ['\"]v([\d\.]+)['\"]\s*$")

ETC_DEFAULT_RE = re.compile("^\[DEFAULT\]\s*$")
ETC_SECTION_RE = re.compile("^\[glance_store\]\s*$")
LOCATIONS = [PACKAGE_INSTALL, PACKAGE_INSTALL_2, SITE_PACKAGE_INSTALL,
             SITE_PACKAGE_INSTALL_2, DEVSTACK_INSTALL]


def detect_glance_install():
    for path in LOCATIONS:
        if os.path.isdir(path):
            return path
    else:
        result = None
        try:
            vprint("Normal cinder install not found, searching for driver")
            result = exe("sudo find / -name datera.py")
            if not result or result.isspace() or "glance-driver" in result:
                return None
            return result.strip().replace(
                "/_drivers/datera.py", "")
        except (subprocess.CalledProcessError, ValueError):
            return None


def find_entry_points_file():
    result = exe("find /usr/ -name 'entry_points.txt' | grep glance_store")
    if not result:
        return None
    return result.strip()


@check("Glance", "driver", "plugin", "image")
def check_glance_driver(config):
    version = get_latest_driver_version(TAGS)
    need_version = version.strip("v")
    loc = detect_glance_install()
    if not loc:
        return ff("Could not detect Glance install location", "6515ADB8")
    dfile = os.path.join(loc, "_drivers/datera.py")
    if not os.path.exists(dfile):
        errloc = os.path.join(loc, "_drivers")
        return ff("Couldn't detect Datera Glance driver install at "
                  "{}".format(errloc), "DD51CEC9")
    version = None
    with io.open(dfile, 'r') as f:
        for line in f:
            version = VERSION_RE.match(line)
            if version:
                version = version.group(1)
                break
    if not version:
        return ff("No version detected for Datera Glance driver at "
                  "{}".format(dfile), "75A8A315")
    if version != need_version:
        return ff("Glance Driver version mismatch, have: {}, want: "
                  "{}".format(version, need_version), "B65FD598")
    entry = find_entry_points_file()
    if not entry:
        return ff("Could not find entry_points.txt file for glance_store",
                  "842A4DB1")
    efound = None
    with io.open(entry) as f:
        for line in f:
            if 'datera' in line:
                efound = line
                break
    if not efound:
        return ff("Could not find 'datera' entry in {}".format(entry),
                  "22DC6275")
    k, v = efound.split("=")
    if k.strip() != 'datera':
        return ff("entry_points.txt entry malformed", "3F9F67BF")
    if v.strip() != 'glance_store._drivers.datera:Store':
        return ff("entry_points.txt entry malformed", "3F9F67BF")

    backend = os.path.join(loc, "backend.py")
    bfound = False
    with io.open(backend) as f:
        for line in f:
            if 'datera' in line:
                bfound = True
                break
            if 'class Indexable' in line:
                break
    if not bfound:
        ff("'datera' has not been added to the 'default_store' StrOpt's "
           "'choices' parameter", "C521E039")


@check("Glance Conf", "driver", "plugin", "config", "image")
def check_glance_conf(config):
    pass
    section = None
    with io.open(ETC, 'r') as f:
        for line in f:
            default = ETC_DEFAULT_RE.match(line)
            if default:
                break
        if not default:
            ff("[DEFAULT] section missing from {}".format(ETC), "228241A8")
        for line in f:
            section = ETC_SECTION_RE.match(line)
            if section:
                break
        if not section:
            return ff("[glance_store] section missing from {}".format(ETC),
                      "AFCBBDD7")
        dsection = []
        section_match = re.compile("^\[.*\]")
        for line in f:
            if section_match.match(line):
                break
            dsection.append(line)

        ip = config['mgmt_ip']
        user = config['username']
        passwd = config['password']

        san_check = False
        user_check = False
        pass_check = False
        stores_check = False
        default_check = False

        for line in dsection:
            if line.startswith("stores"):
                stores_check = True
                if "datera" not in line:
                    ff("datera is not set under 'stores' in {}".format(ETC),
                       "0D862946")
            if line.startswith("default_store"):
                default_check = True
                if "datera" not in line:
                    wf("datera is not set as default_store in {}".format(ETC),
                       "B74CEBC3")
            if line.startswith("datera_san_ip"):
                san_check = True
                if line.split("=")[-1].strip() != ip:
                    ff("datera_san_ip doesn't match mgmt ip", "2330CACB")
            if line.startswith("datera_san_login"):
                user_check = True
                if line.split("=")[-1].strip() != user:
                    ff("datera_san_login doesn't match username",
                       "E9F02293")
            if line.startswith("datera_san_password"):
                pass_check = True
                if line.split("=")[-1].strip() != passwd:
                    ff("datera_san_password doesn't match password",
                       "4B16C4F7")

        if not stores_check:
            ff("'stores' entry not found under [glance_store]", "11F30DCF")
        if not default_check:
            ff("'default_store' entry not found under [glance_store]",
               "540C3008")
        if not san_check:
            ff("'datera_san_ip' entry not found under [glance_store]",
               "42481C71")
        if not user_check:
            ff("'datera_san_login' entry not found under [glance_store]",
               "6E281004")
        if not pass_check:
            ff("'datera_san_password' entry not found under [glance_store]",
               "F5DEC8B1")


def load_checks():
    return [check_glance_driver,
            check_glance_conf]
