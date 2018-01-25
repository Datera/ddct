from __future__ import (print_function, unicode_literals, division,
                        absolute_import)
import io
import os
import shutil
import sys
import uuid


from common import vprint, exe, get_os, idempotent, fix_load

from tabulate import tabulate

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


def no_fix():
    """No-op function"""
    vprint("No fix for this code")


@idempotent
def fix_arp_1():
    """Fixes net.ipv4.conf.all.arp_announce"""
    vprint("Fixing ARP setting")
    exe("sysctl -w net.ipv4.conf.all.arp_announce=2")


@idempotent
def fix_arp_2():
    """Fixes net.ipv4.conf.all.arp_ignore"""
    vprint("Fixing ARP setting")
    exe("sysctl -w net.ipv4.conf.all.arp_ignore=1")


@idempotent
def fix_irq_1():
    """Stops irqbalance services"""
    vprint("Stopping irqbalance service")
    exe("service irqbalance stop")


@idempotent
def fix_cpufreq_1():
    """Installs cpufreq tooling packages"""
    if get_os() == "ubuntu":
        # Install necessary headers and utils
        exe("apt-get install linux-tools-$(uname -r) "
            "linux-cloud-tools-$(uname -r) linux-tools-common -y")
        # Install cpufrequtils package
        exe("apt-get install cpufrequtils -y")
    else:
        # Install packages
        exe("yum install kernel-tools -y")


@idempotent
def fix_cpufreq_2():
    """Updates governer to performance via cpufreq"""
    # Update governor
    exe("cpupower frequency-set --governor performance")
    # Restart service
    if get_os() == "ubuntu":
        exe("service cpufrequtils restart")
    else:
        exe("service cpupower restart")
        exe("systemctl daemon-reload")
    # Remove ondemand rc.d files
    exe("rm -f /etc/rc?.d/*ondemand")


@idempotent
def fix_block_devices_1():
    """Updates GRUB with noop scheduling, requires restart"""
    vprint("Fixing block device settings")
    grub = "/etc/default/grub"
    bgrub = "/etc/default/grub.bak.{}".format(str(uuid.uuid4())[:4])
    vprint("Backing up grub default file to {}".format(bgrub))
    shutil.copyfile(grub, bgrub)
    vprint("Writing new grub default file")
    data = []
    with io.open(grub, "r+") as f:
        for line in f.readlines():
            if ("GRUB_CMDLINE_LINUX_DEFAULT=" in line and
                    "elevator=noop" not in line):
                i = line.rindex("\"")
                lline = list(line)
                if lline[i-1] == "\"":
                    lline.insert(i, "elevator=noop")
                else:
                    lline.insert(i, " elevator=noop")
                line = "".join(lline)
            data.append(line)
    with io.open(grub, "w+") as f:
        print(data)
        f.writelines(data)
    if get_os() == "ubuntu":
        exe("update-grub2")
    else:
        exe("grub2-mkconfig -o /boot/grub2/grub.cfg")


@idempotent
def fix_multipath_1():
    """Installs multipath tooling packages"""
    vprint("Fixing multipath settings")
    if get_os() == "ubuntu":
        exe("apt-get install multipath-tools -y")
    else:
        exe("yum install device-mapper-multipath -y")


@idempotent
def fix_multipath_2():
    """Enables multipathd service"""
    if get_os() == "ubuntu":
        exe("systemctl start multipath-tools")
        exe("systemctl enable multipath-tools")
    else:
        exe("systemctl start multipathd")
        exe("systemctl enable multipathd")


@idempotent
def fix_multipath_conf_1():
    """Writes completely new multipath.conf based off of template"""
    mfile = "/etc/multipath.conf"
    bfile = "/etc/multipath.conf.bak.{}".format(str(uuid.uuid4())[:4])
    if os.path.exists(mfile):
        vprint("Found existing multipath.conf, moving to {}".format(bfile))
        shutil.copyfile(mfile, bfile)
    with io.open("/etc/multipath.conf", "w+") as f:
        if get_os() == "ubuntu":
            f.write(MULTIPATH_CONF.replace("REPLACEME", "timer"))
        else:
            mconf = MULTIPATH_CONF.replace("REPLACEME", "timeout")
            # filter out getuid line which is deprecated in RHEL
            mconf = "\n".join((line for line in mconf.split("\n")
                               if "getuid" not in line))
            f.write(mconf)


fix_dict = {
    "9000C3B6": [fix_arp_1],
    "BDB4D5D8": [fix_arp_2],
    "B19D9FF1": [fix_irq_1],
    "20CEE732": [fix_cpufreq_1, fix_cpufreq_2],
    "A65B6D97": [no_fix],
    "47BB5083": [fix_block_devices_1],
    "2D18685C": [fix_multipath_1, fix_multipath_2],
    "541C10BF": [fix_multipath_2],
    "1D506D89": [fix_multipath_conf_1]}


def print_fixes(plugins):
    print("Supported Fixes")
    if plugins:
        load_plugin_fixes(plugins)
    t = tabulate(
        sorted(map(lambda x: (x[0],
               ", ".join(map(lambda y: y.__doc__, x[1]))),
            fix_dict.items())),
        headers=["Code", "Fix Functions"],
        tablefmt="grid")
    print(t)


def load_plugin_fixes(plugins):
    plugs = fix_load()
    for plugin in plugins:
        if plugin not in plugs:
            print("Unrecognized fix plugin requested:", plugin)
            print("Available fix plugins:", ", ".join(plugins.keys()))
            sys.exit(1)
        fix_dict.update(plugs[plugin].load_fixes())


def run_fixes(codes, config, plugins=None):
    if plugins:
        load_plugin_fixes(plugins)
    for code in codes:
        fixes = fix_dict[code]
        for fix in fixes:
            try:
                fix()
            except TypeError:
                fix(config)
