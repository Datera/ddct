from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import re

from common import exe_check, exe, ff, wf, check


KCTL_MA_RE = re.compile("Major:\"(\d+)\",")
KCTL_MI_RE = re.compile("Minor:\"(\d+)\",")
KPATH_RE = re.compile("path=(.*?) ;")

SUPPORTED_MAJOR = 1
SUPPORTED_MINOR = 6


def calc_version(m1, m2):
    return int(m1) * 100 + int(m2)


@check("K8S", "driver", "plugin", "local")
def check_kubernetes_driver_flex(config):
    # Is kubectl present?
    if not exe_check("which kubectl"):
        return ff("Could not detect kubectl installation", "572B0511")
    # Does kubectl have a supported version?
    kversion = exe("kubectl version").strip().split("\n")
    for line in kversion:
        m1 = KCTL_MA_RE.search(line)
        m2 = KCTL_MI_RE.search(line)
        if not m1 and m2:
            return ff("Could not detect kubectl version", "C1802A6E")
        supported = calc_version(SUPPORTED_MAJOR, SUPPORTED_MINOR)
        major = m1.group(1)
        minor = m2.group(1)
        found = calc_version(major, minor)
        if found < supported:
            return ff("Kubectl has version {}, which is lower than supported "
                      "version {}".format(found, supported), "D2DA6596")
    # Are dependencies installed?
    if not exe_check("which mkfs"):
        ff("mkfs is not installed", "FE13A328")
    if not exe_check("which iscsiadm"):
        ff("sg3_utils does not appear to be installed", "94BF0B77")
    # Is attach-detach disabled in kubelet?
    exstart = exe("systemctl show kubelet.service | grep ExecStart")
    if "--enable-controller-attach-detach=false" not in exstart:
        wf("Attach-detach is enabled in kublet's systemctl entry.  Run "
           "--enable-controller-attach-detach=false when starting kubelet "
           "to disable", "5B3729F2")
    if "Active: active" in exe("systemctl status kubelet"):
        kpath = KPATH_RE.search(exstart).group(1)
        exstart = exe("ps -ef | grep {} | grep -v grep".format(kpath))
        if "--enable-controller-attach-detach=false" not in exstart:
            ff("Attach-detach is enabled in kublet.  Run "
               "--enable-controller-attach-detach=false when starting kubelet "
               "to disable", "86FFD7F2")
    else:
        ff("The kubelet service is not running", "0762A89B")
    # Agents are running?
    pods = exe("kubectl --namespace=datera get pods").strip()
    if not pods:
        return ff("Installer agents and provisioner agents are not running",
                  "244C0B34")
    installer_agent = False
    provisioner_agent = False
    for line in pods.split("\n"):
        if "datera-installer-agent" in line:
            installer_agent = True
        if "datera-provisioner-agent" in line:
            provisioner_agent = True
    if not installer_agent:
        ff("Installer agents not found", "08193032")
    if not provisioner_agent:
        ff("Provisioner agents not found", "3AAF82CA")


def load_checks():
    return [check_kubernetes_driver_flex]
