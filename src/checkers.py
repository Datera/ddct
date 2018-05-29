from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os
import sys
import time
import threading

from common import vprint, exe_check, ff, parse_mconf, get_os, check_load, exe
from common import check, wf

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

SUPPORTED_OS_TYPES = ["ubuntu", "debian", "centos", "rhel"]
FETCH_SO_URL = ("https://raw.githubusercontent.com/Datera/docker-driver/"
                "master/scripts/assets/fetch_device_serial_no.sh")
UDEV_URL = ("https://raw.githubusercontent.com/Datera/docker-driver/master/"
            "scripts/assets/99-iscsi-luns.rules")


@check("OS", "basic", "os", "local")
def check_os(config):
    if not get_os():
        return ff("Unsupported Operating System. Supported operating systems:"
                  "{}".format(SUPPORTED_OS_TYPES), "3C47368")


@check("ISCSI", "basic", "iscsi", "local")
def check_iscsi(config):
    vprint("Checking ISCSI settings")
    if not exe_check("which iscsiadm"):
        if get_os() == "ubuntu":
            fix = "apt-get install open-iscsi"
        elif get_os() == "centos":
            fix = "yum install iscsi-initiator-utils"
        ff("iscsiadm is not available, has open-iscsi been installed?",
           "EFBB085C", fix=fix)


@check("UDEV", "basic", "udev", "local")
def check_udev(config):
    vprint("Checking udev rules config")
    frules = "/etc/udev/rules.d/99-iscsi-luns.rules"
    if not os.path.exists(frules):
        fix = "A copy of the udev rules are available from: {}".format(
            UDEV_URL)
        ff("Datera udev rules are not installed", "1C8F2E07", fix=fix)
    snum = "/sbin/fetch_device_serial_no.sh"
    if not os.path.exists(snum):
        fix = ("A copy of fetch_device_serial_no.sh is available at: "
               "{}".format(FETCH_SO_URL))
        ff("fetch_device_serial_no.sh is missing from /sbin", "6D03F50B",
           fix=fix)


@check("ARP", "basic", "arp", "local")
def check_arp(config):
    vprint("Checking ARP settings")
    if not exe_check("sysctl --all 2>/dev/null | "
                     "grep 'net.ipv4.conf.all.arp_announce = 2'",
                     err=False):
        fix = "sysctl net.ipv4.conf.all.arp_announce=2"
        ff("net.ipv4.conf.all.arp_announce != 2 in sysctl", "9000C3B6",
           fix=fix)
    if not exe_check("sysctl --all 2>/dev/null | "
                     "grep 'net.ipv4.conf.all.arp_ignore = 1'",
                     err=False):
        fix = "sysctl net.ipv4.conf.all.arp_ignore=1"
        ff("net.ipv4.conf.all.arp_ignore != 1 in sysctl", "BDB4D5D8", fix=fix)


@check("IRQ", "basic", "irq", "local")
def check_irq(config):
    vprint("Checking irqbalance settings, (should be turned off)")
    if not exe_check("which systemctl"):
        if not exe_check("service irqbalance status | "
                         "grep 'Active: active'",
                         err=True):
            fix = "service irqbalance stop"
            return ff("irqbalance is active", "B19D9FF1", fix=fix)
    else:
        if not exe_check("systemctl status irqbalance | "
                         "grep 'Active: active'",
                         err=True):
            fix = "systemctl stop irqbalance && systemctl disable irqbalance"
            return ff("irqbalance is active", "B19D9FF1", fix=fix)


@check("CPUFREQ", "basic", "cpufreq", "local")
def check_cpufreq(config):
    vprint("Checking cpufreq settings")
    if not exe_check("which cpupower"):
        if get_os() == "ubuntu":
            version = exe("uname -r").strip()
            fix = "apt-get install linux-tools-{}".format(version)
        else:
            # RHEL puts this stuff in kernel-tools
            fix = "yum install kernel-tools"
        return ff("cpupower is not installed", "20CEE732", fix=fix)
    if not exe_check("cpupower frequency-info --governors | "
                     "grep performance",
                     err=False):
        fix = ("No-fix -- if this system is a VM governors might not be "
               "available and this check can be ignored")
        return ff("No 'performance' governor found for system", "333FBD45",
                  fix=fix)


@check("Block Devices", "basic", "block_device", "local")
def check_block_devices(config):
    vprint("Checking block device settings")
    grub = "/etc/default/grub"
    if not os.path.exists(grub):
        return ff("Could not find default grub file at {}".format(grub),
                  "6F7B6A25")
    with io.open(grub, "r") as f:
        data = f.readlines()
        line = filter(lambda x: x.startswith("GRUB_CMDLINE_LINUX_DEFAULT="),
                      data)
        line2 = filter(lambda x: x.startswith("GRUB_CMDLINE_LINUX="), data)
        if len(line) != 1 and len(line2) != 1:
            return ff("GRUB_CMDLINE_LINUX_DEFAULT and GRUB_CMDLINE_LINUX are"
                      " missing from GRUB file", "A65B6D97")
        if ((len(line) > 0 and "elevator=noop" not in line[0]) and
                (len(line2) > 0 and "elevator=noop" not in line2[0])):
            fix = ("Add 'elevator=noop' to /etc/default/grub in the "
                   "'GRUB_CMDLINE_LINUX_DEFAULT' line")
            return ff("Scheduler is not set to noop", "47BB5083", fix=fix)


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
    mfile = "/etc/multipath.conf"
    if not os.path.exists(mfile):
        fix = "copy multipath.conf file from Datera deployment guide"
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
        if get_os() == "ubuntu":
            ct = False
            for d in defaults[1]:
                if 'checker_timer' in d:
                    ct = True
            if not ct:
                ff("defaults section missing 'checker_timer'",
                   "FCFE3444", fix=fix)
        else:
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


@check("MGMT", "basic", "connection", "local")
def mgmt_check(config):
    mgmt = config["mgmt_ip"]
    if not exe_check("ping -c 2 -W 1 {}".format(mgmt), err=False):
        ff("Could not ping management ip {}".format(mgmt), "65FC68BB")
    timeout = 5
    while not exe_check(
            "ip neigh show | grep {} | grep REACHABLE".format(mgmt)):
        timeout -= 1
        time.sleep(1)
        if timeout < 0:
            fix = "Check the connection to {}".format(mgmt)
            ff("Arp state for mgmt [{}] is not 'REACHABLE'".format(mgmt),
               "BF6A912A", fix=fix)
            break


@check("VIP1", "basic", "connection", "local")
def vip1_check(config):
    vip1 = config["vip1_ip"]
    if not exe_check("ping -c 2 -W 1 {}".format(vip1), err=False):
        ff("Could not ping vip1 ip {}".format(vip1), "1827147B")
    timeout = 5
    while not exe_check(
            "ip neigh show | grep {} | grep REACHABLE".format(vip1)):
        timeout -= 1
        time.sleep(1)
        if timeout < 0:
            ff("Arp state for vip1 [{}] is not 'REACHABLE'".format(vip1),
               "3C33D70D")
            break


@check("VIP2", "basic", "connection", "local")
def vip2_check(config):
    vip2 = config.get("vip2_ip")
    if vip2 and not exe_check("ping -c 2 -W 1 {}".format(vip2), err=False):
        ff("Could not ping vip2 ip {}".format(vip2), "3D76CE5A")
    timeout = 5
    while not exe_check(
            "ip neigh show | grep {} | grep REACHABLE".format(vip2)):
        timeout -= 1
        time.sleep(1)
        if timeout < 0:
            ff("Arp state for vip2 [{}] is not 'REACHABLE'".format(vip2),
               "4F6B8D91")
            break


@check("CALLHOME", "basic", "setup", "local")
def callhome_check(config):
    api = config["api"]
    if not api.system.get()['callhome_enabled']:
        wf("Callhome is not enabled", "675E2887")


check_list = [check_os,
              check_iscsi,
              check_udev,
              check_arp,
              check_irq,
              check_cpufreq,
              check_block_devices,
              check_multipath,
              check_multipath_conf,
              mgmt_check,
              vip1_check,
              vip2_check,
              callhome_check]


def load_plugin_checks(plugins):
    plugs = check_load()
    for plugin in plugins:
        if plugin not in plugs:
            print("Unrecognized check plugin requested:", plugin)
            print("Available check plugins:", ", ".join(plugs.keys()))
            sys.exit(1)
        check_list.extend(plugs[plugin].load_checks())


def load_checks(config, plugins=None, tags=None, not_tags=None):
    if plugins:
        load_plugin_checks(plugins)
    threads = []

    # Filter checks to be executed based on tags passed in
    checks = check_list
    if tags:
        checks = filter(lambda x: any([t in x._tags for t in tags]),
                        checks)
    if not_tags:
        checks = filter(lambda x: not any([t in x._tags for t in not_tags]),
                        checks)
    for ck in checks:
        thread = threading.Thread(target=ck, args=(config,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()


def print_tags(config, plugins=None):
    if plugins:
        load_plugin_checks(plugins)
    tags = set()
    for ck in check_list:
        for tag in ck._tags:
            tags.add(tag)
    print(tabulate(sorted(map(lambda x: [x], tags)), headers=["Tags"],
                   tablefmt="grid"))

# Possible additional checks
# ethtool -S
# netstat -F (retrans)
