from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import re

from common import exe_check, exe, ff, check


KCTL_MA_RE = re.compile("Major:\"(\d+)\",")
KCTL_MI_RE = re.compile("Minor:\"(\d+)\",")
KPATH_RE = re.compile("path=(.*?) ;")

SUPPORTED_MAJOR = 1
SUPPORTED_MINOR = 13


def calc_version(m1, m2):
    return int(m1) * 100 + int(m2)


@check("K8S", "driver", "plugin", "local")
def check_kubernetes_driver_csi(config):
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
    if not exe_check("which iscsiadm"):
        ff("open-iscsi does not appear to be installed", "94BF0B77")
    # Is attach-detach disabled in kubelet?
    exstart = exe("systemctl show kubelet.service | grep ExecStart")
    if not exstart:
        if exe_check("microk8s.kubectl"):
            ff("kubelet service not detected.  microk8s is not currently "
               "supported", "995EA49E")
            return
        else:
            ff("kubelet service not detected. 'systemctl show kubelet.service'"
               " returned nothing", "F3C47DDF")
    if "--allow-privileged" not in exstart:
        ff("--allow-privileged is not enabled in kublet's systemctl entry.  "
           "Run --allow-privileged=true when starting kubelet "
           "to enable", "7475B000")
    if "Active: active" in exe("systemctl status kubelet"):
        kpath = KPATH_RE.search(exstart).group(1)
        exstart = exe("ps -ef | grep {} | grep -v grep".format(kpath))
        if "--enable-controller-attach-detach=false" in exstart:
            ff("Attach-detach is disabled in kublet.  Run "
               "--enable-controller-attach-detach=true when starting kubelet "
               "to enable", "86FFD7F2")
    else:
        ff("The kubelet service is not running", "0762A89B")
    # iscsi-recv is running?
    if not exe_check("ps -ef | grep iscsi-recv | grep -v grep"):
        fix = "Run ./setup_iscsi.sh from the datera-csi repository"
        ff("iscsi-recv binary is not running.", "A8B6BA35", fix=fix)

    # Agents are running?
    pods = exe("kubectl --namespace=kube-system get pods").strip()
    if not pods:
        return ff("CSI plugin pods are not running.", "49BDC893",
                  fix="Install the CSI plugin deployment yaml.  "
                      "'kubectl create -f csi.yaml'")
    controller_pod = False
    node_pods = False
    for line in pods.split("\n"):
        if "csi-provisioner-0" in line:
            controller_pod = True
        if "csi-node-" in line:
            node_pods = True
    if not controller_pod:
        ff("Controller pod not found", "17FF7B78")
    if not node_pods:
        ff("At least one Node pod not found", "2FD6A7B4")


def load_checks():
    return [check_kubernetes_driver_csi]
