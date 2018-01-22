#!/usr/bin/env python

from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os
import shutil
import uuid

from common import vprint, exe, exe_check, ff, sf, parse_mconf

# Using string REPLACEME instead of normal string formatting because it's
# easier than escaping everything
MULTIPATH_CONF = """
defaults {
    checker_REPLACEME 5

}

devices {

    device {

    vendor "DATERA"

    product "IBLOCK"

    getuid_callout "/lib/udev/scsi_id --whitelisted --replace- whitespace"""\
"""--page=0x80 --device=/dev/%n"

    path_grouping_policy group_by_prio

    path_checker tur

    prio alua

    path_selector "queue-length 0"

    hardware_handler "1 alua"

    failback 5

    }

}

blacklist {

    device {

    vendor ".*"

    product ".*"

    }

}

blacklist_exceptions {

    device {

    vendor "DATERA.*"

    product "IBLOCK.*"

    }

}
"""


def get_os():
    if exe_check("which apt-get", err=False):
        return "ubuntu"
    if exe_check("which yum", err=False):
        return "centos"


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


def fix_arp(*args, **kwargs):
    vprint("Fixing ARP settings")
    exe("sysctl -w net.ipv4.conf.all.arp_announce=2")
    exe("sysctl -w net.ipv4.conf.all.arp_ignore=1")


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
            return ff("IRQ", "irqbalance is active", "3069D981")
    sf("IRQ")


def fix_irq(*args, **kwargs):
    vprint("Stopping irqbalance service")
    exe("service irqbalance stop")


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
            " governors might not be available and this check should be"
            " disabled", "333FBD45")
    sf("CPUFREQ")


def fix_cpufreq(*args, **kwargs):
    if kwargs["os_version"] == "ubuntu":
        # Install necessary headers and utils
        exe("apt-get install linux-tools-$(uname -r) "
            "linux-cloud-tools-$(uname -r) linux-tools-common -y")
        # Install cpufrequtils package
        exe("apt-get install cpufrequtils -y")
    elif kwargs["os_version"] == "centos":
        # Install packages
        exe("yum install kernel-tools -y")
    # Update governor
    exe("cpupower frequency-set --governor performance")
    # Restart service
    if kwargs["os_version"] == "ubuntu":
        exe("service cpufrequtils restart")
    else:
        exe("service cpupower restart")
        exe("systemctl daemon-reload")
    # Remove ondemand rc.d files
    exe("rm -f /etc/rc?.d/*ondemand")


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


def fix_block_devices(*args, **kwargs):
    vprint("Fixing block device settings")
    grub = "/etc/default/grub"
    bgrub = "/etc/default/grub.bak.{}".format(str(uuid.uuid4())[:4])
    vprint("Backing up grub default file to {}".format(bgrub))
    shutil.copyfile(grub, bgrub)
    vprint("Writing new grub default file")
    data = []
    with io.open(grub, "r+") as f:
        for line in f.readlines():
            if "GRUB_CMDLINE_LINUX=" in line and "elevator=noop" not in line:
                line = "=".join(("GRUB_CMDLINE_LINUX", "\"" + " ".join((
                    line.split("=")[-1].strip("\""), "elevator=noop"))))
            data.append(line)
    with io.open(grub, "w+") as f:
        f.writelines(data)
    if kwargs["os_version"] == "ubuntu":
        exe("update-grub2")
    elif kwargs["os_version"] == "centos":
        exe("grub2-mkconfig -o /boot/grub2/grub.cfg")


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
            ff(name, "multipathd not enabled", "8D6CC096")
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


def fix_multipath(*args, **kwargs):
    vprint("Fixing multipath settings")
    if kwargs["os_version"] == "ubuntu":
        exe("apt-get install multipath-tools -y")
    elif kwargs["os_version"] == "centos":
        exe("yum install device-mapper-multipath -y")
    mfile = "/etc/multipath.conf"
    bfile = "/etc/multipath.conf.bak.{}".format(str(uuid.uuid4())[:4])
    if os.path.exists(mfile):
        vprint("Found existing multipath.conf, moving to {}".format(bfile))
        shutil.copyfile(mfile, bfile)
    with io.open("/etc/multipath.conf", "w+") as f:
        if kwargs["os_version"] == "ubuntu":
            f.write(MULTIPATH_CONF.replace("REPLACEME", "timer"))
        elif kwargs["os_version"] == "centos":
            mconf = MULTIPATH_CONF.replace("REPLACEME", "timeout")
            # filter out getuid line which is deprecated in RHEL
            mconf = "\n".join((line for line in mconf.split("\n")
                               if "getuid" not in line))
            f.write(mconf)
    if kwargs["os_version"] == "ubuntu":
        exe("systemctl start multipath-tools")
        exe("systemctl enable multipath-tools")
    elif kwargs["os_version"] == "centos":
        exe("systemctl start multipathd")
        exe("systemctl enable multipathd")


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


def client_fix(args):
    pass
