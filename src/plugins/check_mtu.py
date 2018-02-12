from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import re
import subprocess

from common import vprint, exe, exe_check, ff, check, parse_route_table

import ipaddress

MTU_RE = re.compile(r"^.*mtu (\d+) .*$")

# Python 2/3 compatibility
try:
    str = unicode
except NameError:
    pass


iface_dict = {"MGMT": "mgt1",
              "VIP1": "netA1",
              "VIP2": "netA2"}


def get_interface_for_ip(ip):
    ipobj = ipaddress.ip_address(str(ip))
    rt = parse_route_table()
    for net, iface in rt:
        if ipobj in net.network:
            return iface
    None


def check_mtu(name, ip, config):
    cname = iface_dict[name]
    sif = get_interface_for_ip(ip)
    if not sif:
        return ff("Couldn't find interface with network matching ip {}"
                  "".format(ip), "710BFC7E")
    try:
        match = MTU_RE.match(exe("ip ad show {} | grep mtu".format(sif)))
    except subprocess.CalledProcessError:
        return ff("Couldn't find client {} interface MTU".format(name),
                  "CBF8CC4C")
    if not match:
        return ff("Couldn't find client {} interface MTU".format(name),
                  "CBF8CC4C")
    local_mtu = match.groups(1)[0]

    cluster_mtu = None
    api = config['api']
    if name == "MGMT":
        cluster_mtu = api.system.network.mgmt_vip.get()['network_paths'][
            0]['mtu']
    elif name == "VIP1":
        cluster_mtu = api.system.network.get()['access_vip'][
            'network_paths'][0]['mtu']
    elif name == "VIP2":
        cluster_mtu = api.system.network.get()['access_vip'][
            'network_paths'][0]['mtu']
    if not cluster_mtu:
        return ff("Couldn't find cluster {} interface MTU".format(cname),
                  "057AF23D")
    if str(local_mtu) != str(cluster_mtu):
        ff("Local interface {} MTU does not match cluster {} interface MTU "
           "[{} != {}]".format(sif, cname, local_mtu, cluster_mtu), "D7F667BC")
    # Ping check
    if not exe_check("ping -s 32000 -c 2 -W 1 {}".format(ip)):
        ff("Could not ping interface with large (32k) packet size, packet"
           "fragmentation may not be working correctly", "A4CA0D72")


@check("MGMT MTU", "connection", "plugin")
def check_mgmt(config):
    vprint("Checking mgmt interface mtu match")
    mgmt = config['mgmt_ip']
    check_mtu("MGMT", mgmt, config)


@check("VIP1 MTU", "connection", "plugin")
def check_vip1(config):
    vprint("Checking vip1 interface mtu match")
    vip1 = config['vip1_ip']
    check_mtu("VIP1", vip1, config)


@check("VIP2 MTU", "connection", "plugin")
def check_vip2(config):
    vprint("Checking vip2 interface mtu match")
    vip2 = config['vip2_ip']
    check_mtu("MGMT", vip2, config)


def load_checks():
    return [check_mgmt, check_vip1, check_vip2]
