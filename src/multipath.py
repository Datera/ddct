from __future__ import (print_function, unicode_literals, division,
                        absolute_import)
import io
import os

from common import vprint, parse_mconf, check, exe_check, ff, wf, get_os
from common import ASSETS, UBUNTU, CENTOS6, CENTOS7


CENTOS6_CONF = os.path.join(ASSETS, "centos6.mconf")
CENTOS7_CONF = os.path.join(ASSETS, "centos7.mconf")
UBUNTU_CONF = os.path.join(ASSETS, "ubuntu.mconf")

CONFS = {CENTOS6: CENTOS6_CONF,
         CENTOS7: CENTOS7_CONF,
         UBUNTU: UBUNTU_CONF}


@check("Multipath", "basic", "multipath", "local")
def check_multipath(config):
    vprint("Checking multipath settings")
    if not exe_check("which multipath", err=False):
        ff("Multipath binary could not be found, is it installed?",
           "2D18685C")
    if not exe_check("which systemctl"):
        if not exe_check("service multipathd status | grep 'Active: active'",
                         err=False):
            fix = "service multipathd start"
            ff("multipathd not enabled", "541C10BF", fix=fix)
    else:
        if not exe_check("systemctl status multipathd | grep 'Active: active'",
                         err=False):
            fix = "systemctl start multipathd"
            ff("multipathd not enabled", "541C10BF", fix=fix)


@check("Multipath Conf", "basic", "multipath", "local")
def check_multipath_conf(config):
    dist = get_os()
    vfile = CONFS.get(dist)
    if not vfile:
        wf("No supported multipath.conf file for: {}".format(dist), "381CE248")
    mfile = "/etc/multipath.conf"
    if not os.path.exists(mfile):
        fix = ("copy multipath.conf file from Datera deployment guide or"
               " the {} folder on your system".format(ASSETS))
        return ff("/etc/multipath.conf file not found", "1D506D89", fix=fix)
    with io.open(mfile, 'r') as f:
        mconf = parse_mconf(f.read())

    # Check defaults section
    defaults = filter(lambda x: x[0] == 'defaults', mconf)
    fix = ("check the example multipath.conf file from Datera deployment"
           "guide")
    if not defaults:
        ff("Missing defaults section", "1D8C438C", fix=fix)

    else:
        defaults = defaults[0]
        ct = False
        for d in defaults[1]:
            if 'checker_timeout' in d:
                ct = True
        if not ct:
            ff("defaults section missing 'checker_timeout'",
               "70191A9A", fix=fix)

    # Check devices section
    devices = filter(lambda x: x[0] == 'devices', mconf)
    if not devices:
        ff("Missing devices section", "797A6031", fix=fix)
    else:
        devices = devices[0][1]
        dat_block = None
        for _, device in devices:
            ddict = {}
            for entry in device:
                ddict[entry[0]] = entry[1]
            if ddict['vendor'] == 'DATERA':
                dat_block = ddict
        if not dat_block:
            return ff("No DATERA device section found", "99B9D136", fix=fix)

        if not dat_block['product'] == "IBLOCK":
            ff("Datera 'product' entry should be \"IBLOCK\"", "A9DF3F8C",
               fix=fix)

    # Blacklist exceptions
    be = filter(lambda x: x[0] == 'blacklist_exceptions', mconf)
    if not be:
        ff("Missing blacklist_exceptions section", "B8C8A19C")
    else:
        be = be[0][1]
        dat_block = None
        for _, device in be:
            bdict = {}
            for entry in device:
                bdict[entry[0]] = entry[1]
            if bdict['vendor'] == 'DATERA.*':
                dat_block = bdict
        if not dat_block:
            ff("No Datera blacklist_exceptions section found",
               "09E37E51", fix=fix)
        if dat_block['vendor'] != 'DATERA.*':
            ff("Datera blacklist_exceptions vendor entry malformed",
               "9990F32F", fix=fix)
        if dat_block['product'] != 'IBLOCK.*':
            ff("Datera blacklist_exceptions product entry malformed",
               "642753A0", fix=fix)


def load_checks():
    return [check_multipath, check_multipath_conf]
