from __future__ import (print_function, unicode_literals, division,
                        absolute_import)
import io
import os
import shutil
import sys
import uuid


from common import vprint, exe, get_os, idempotent, fix_load, load_run_fixes
from common import save_run_fixes, UBUNTU

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
    if get_os() == UBUNTU:
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
    if get_os() == UBUNTU:
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
    if get_os() == UBUNTU:
        exe("update-grub2")
    else:
        exe("grub2-mkconfig -o /boot/grub2/grub.cfg")


@idempotent
def fix_multipath_1():
    """Installs multipath tooling packages"""
    vprint("Fixing multipath settings")
    if get_os() == UBUNTU:
        exe("apt-get install multipath-tools -y")
    else:
        exe("yum install device-mapper-multipath -y")


@idempotent
def fix_multipath_2():
    """Enables multipathd service"""
    if get_os() == UBUNTU:
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
        if get_os() == UBUNTU:
            f.write(MULTIPATH_CONF.replace("REPLACEME", "timer"))
        else:
            mconf = MULTIPATH_CONF.replace("REPLACEME", "timeout")
            # filter out getuid line which is deprecated in RHEL
            mconf = "\n".join((line for line in mconf.split("\n")
                               if "getuid" not in line))
            f.write(mconf)


fix_dict = {
    "057AF23D": [no_fix],
    "0762A89B": [],
    "08193032": [],
    "09E37E51": [],
    "0BB2848F": [],
    "0D862946": [],
    "11F30DCF": [],
    "17FF7B78": [],
    "1827147B": [],
    "1C8F2E07": [],
    "1D506D89": [fix_multipath_conf_1],
    "1D8C438C": [],
    "20CEE732": [fix_cpufreq_1, fix_cpufreq_2],
    "228241A8": [],
    "22DC6275": [],
    "2330CACB": [],
    "244C0B34": [],
    "2D18685C": [fix_multipath_1, fix_multipath_2],
    "2FD6A7B4": [],
    "333FBD45": [],
    "3A6A78D1": [],
    "3AAF82CA": [],
    "3C33D70D": [],
    "3D76CE5A": [],
    "3F9F67BF": [],
    "42481C71": [],
    "42BAAC76": [],
    "47BB5083": [fix_block_devices_1],
    "49BDC893": [],
    "4B16C4F7": [],
    "4F6B8D91": [],
    "525BAAB0": [],
    "540C3008": [],
    "541C10BF": [fix_multipath_2],
    "572B0511": [],
    "5B3729F2": [],
    "5B6EFC71": [],
    "5FEC0454": [],
    "621A6F51": [],
    "642753A0": [],
    "6515ADB8": [],
    "65FC68BB": [],
    "675E2887": [],
    "680E61DB": [],
    "6C531C5D": [],
    "6D03F50B": [],
    "6E281004": [],
    "6F7B6A25": [],
    "70191A9A": [],
    "710BFC7E": [],
    "7475B000": [],
    "75A8A315": [],
    "797A6031": [],
    "7B98CFA1": [],
    "8208B9E7": [],
    "842A4DB1": [],
    "86FFD7F2": [],
    "8A28D615": [],
    "8DBC87E8": [],
    "9000C3B6": [fix_arp_1],
    "945148B0": [],
    "94BF0B77": [],
    "95C9B3AC": [],
    "995EA49E": [],
    "9990F32F": [],
    "99B9D136": [],
    "A06CD19F": [],
    "A2EED511": [],
    "A37FD778": [],
    "A433E6C6": [],
    "A4402034": [],
    "A4CA0D72": [],
    "A65B6D97": [no_fix],
    "A8B6BA35": [],
    "A9DF3F8C": [],
    "AA27965F": [],
    "AF3DB8B3": [],
    "AFCBBDD7": [],
    "B106D1CD": [],
    "B19D9FF1": [fix_irq_1],
    "B3BF691D": [],
    "B5D29621": [],
    "B65FD598": [],
    "B74CEBC3": [],
    "B845D5B1": [],
    "B8C8A19C": [],
    "BDB4D5D8": [fix_arp_2],
    "BF6A912A": [],
    "C1802A6E": [],
    "C2B8C696": [],
    "C521E039": [],
    "C5B86514": [],
    "CA9AA865": [],
    "CBF8CC4C": [],
    "D2DA6596": [],
    "D7F667BC": [],
    "DD51CEC9": [],
    "D3E55910": [],
    "E29BF18A": [],
    "E48C1907": [],
    "E9F02293": [],
    "EB22737E": [],
    "EC2D3621": [],
    "EFBB085C": [],
    "F3C47DDF": [],
    "F5DEC8B1": [],
    "F6A49337": [],
    "FCFE3444": [],
    "FE13A328": [],
}


def print_fixes(plugins):
    print("Supported Fixes")
    if plugins:
        load_plugin_fixes(plugins)
    fd = filter(lambda x: x[1], fix_dict.items())
    t = tabulate(
        sorted(map(lambda x: (x[0],
               ", ".join(map(lambda y: y.__doc__, x[1]))), fd)),
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
    load_run_fixes()
    reraise = False
    try:
        if plugins:
            load_plugin_fixes(plugins)
        for code in codes:
            fixes = fix_dict[code]
            for fix in fixes:
                try:
                    fix()
                except TypeError:
                    fix(config)
    except Exception:
        reraise = True
    save_run_fixes()
    if reraise:
        raise
