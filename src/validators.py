from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os

from common import vprint, exe_check, ff, sf, parse_mconf, get_os


def check_os():
    if not get_os():
        return ff("OS", "Unsupported Operating System", "3C47368")
    return sf("OS")


def check_arp():
    vprint("Checking ARP settings")
    name = "ARP"
    if not exe_check("sysctl --all 2>/dev/null | "
                     "grep 'net.ipv4.conf.all.arp_announce = 2'",
                     err=False):
        ff(name, "net.ipv4.conf.all.arp_announce != 2 in sysctl", "9000C3B6")
    if not exe_check("sysctl --all 2>/dev/null | "
                     "grep 'net.ipv4.conf.all.arp_ignore = 1'",
                     err=False):
        ff(name, "net.ipv4.conf.all.arp_ignore != 1 in sysctl", "BDB4D5D8")
    sf("ARP")


def check_irq():
    vprint("Checking irqbalance settings, (should be turned off)")
    if not exe_check("which systemctl"):
        if not exe_check("service irqbalance status | "
                         "grep 'Active: active'",
                         err=True):
            return ff("IRQ", "irqbalance is active", "B19D9FF1")
    else:
        if not exe_check("systemctl status irqbalance | "
                         "grep 'Active: active'",
                         err=True):
            return ff("IRQ", "irqbalance is active", "B19D9FF1")
    sf("IRQ")


def check_cpufreq():
    vprint("Checking cpufreq settings")
    if not exe_check("which cpupower"):
        return ff("CPUFREQ", "cpupower is not installed", "20CEE732")
    if not exe_check("cpupower frequency-info --governors | "
                     "grep performance",
                     err=False):
        return ff(
            "CPUFREQ",
            "No 'performance' governor found for system.  If this is a VM,"
            " governors might not be available and this check can be ignored"
            "333FBD45")
    sf("CPUFREQ")


def check_block_devices():
    vprint("Checking block device settings")
    name = "Block Devices"
    grub = "/etc/default/grub"
    with io.open(grub, "r") as f:
        line = filter(lambda x: x.startswith("GRUB_CMDLINE_LINUX="),
                      f.readlines())
        if len(line) != 1:
            return ff(name, "Grub file appears non-standard", "A65B6D97")
        if "elevator=noop" not in line:
            return ff(name, "Scheduler is not set to noop", "47BB5083")
    sf(name)


def check_multipath():
    name = "Multipath"
    vprint("Checking multipath settings")
    if not exe_check("which multipath", err=False):
        ff(name, "Multipath binary could not be found, is it installed?",
           "2D18685C")
    if not exe_check("which systemctl"):
        if not exe_check("service multipathd status | grep 'Active: active'",
                         err=False):
            ff(name, "multipathd not enabled", "541C10BF")
    else:
        if not exe_check("systemctl status multipathd | grep 'Active: active'",
                         err=False):
            ff(name, "multipathd not enabled", "541C10BF")
    sf(name)


def check_multipath_conf():
    name = "Multipath Conf"
    mfile = "/etc/multipath.conf"
    if not os.path.exists(mfile):
        return ff(name, "/etc/multipath.conf file not found", "1D506D89")
    with io.open(mfile, 'r') as f:
        mconf = parse_mconf(f.read())

    # Check defaults section
    defaults = filter(lambda x: x[0] == 'defaults', mconf)
    if not defaults:
        ff(name, "Missing defaults section", "1D8C438C")

    else:
        defaults = defaults[0]
        if get_os() == "ubuntu":
            ct = False
            for d in defaults[1]:
                if 'checker_timer' in d:
                    ct = True
            if not ct:
                ff(name, "defaults section missing 'checker_timer'",
                   "FCFE3444")
        else:
            ct = False
            for d in defaults[1]:
                if 'checker_timeout' in d:
                    ct = True
            if not ct:
                ff(name, "defaults section missing 'checker_timeout'",
                   "70191A9A")

    # Check devices section
    devices = filter(lambda x: x[0] == 'devices', mconf)
    if not devices:
        ff(name, "Missing devices section", "797A6031")
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
            return ff(name, "No DATERA device section found", "99B9D136")

        if not dat_block['product'] == "IBLOCK":
            ff(name, "Datera 'product' entry should be \"IBLOCK\"", "A9DF3F8C")

    # Blacklist exceptions
    be = filter(lambda x: x[0] == 'blacklist_exceptions', mconf)
    if not be:
        ff(name, "Missing blacklist_exceptions section", "B8C8A19C")
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
            ff(name, "No Datera blacklist_exceptions section found",
               "09E37E51")
        if dat_block['vendor'] != 'DATERA.*':
            ff(name, "Datera blacklist_exceptions vendor entry malformed",
               "9990F32F")
        if dat_block['product'] != 'IBLOCK.*':
            ff(name, "Datera blacklist_exceptions product entry malformed",
               "642753A0")
    sf(name)


def client_check(config):

    checks = [check_os,
              check_arp,
              check_irq,
              check_cpufreq,
              check_block_devices,
              check_multipath,
              check_multipath_conf]

    list(map(lambda x: x(), checks))


def connection_check(config):
    mgmt = config["mgmt_ip"]
    vip1 = config["vip1_ip"]
    vip2 = config.get("vip2_ip")
    if not exe_check("ping -c 2 -W 1 {}".format(mgmt), err=False):
        ff("MGMT", "Could not ping management ip {}".format(mgmt), "65FC68BB")
    else:
        sf("MGMT")
    if not exe_check("ping -c 2 -W 1 {}".format(vip1), err=False):
        ff("VIP1", "Could not ping vip1 ip {}".format(vip1), "1827147B")
    else:
        sf("VIP1")
    if vip2 and not exe_check("ping -c 2 -W 1 {}".format(vip2), err=False):
        ff("VIP2", "Could not ping vip2 ip {}".format(vip2), "3D76CE5A")
    elif vip2:
        sf("VIP2")
