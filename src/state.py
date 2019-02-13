from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import distro
import psutil

from common import hs


GBi = (1024 * 1024 * 1024.0)


def get_host_state(config):
    hs("os", distro.os_release_info())
    hs("cpus(logical)", psutil.cpu_count())
    hs("cpus(physical)", psutil.cpu_count(logical=False))
    hs("memory_total", str(round(
        psutil.virtual_memory().total / GBi, 2)) + " GBi")
    hs("memory_free", str(round(
        psutil.virtual_memory().free / GBi, 2)) + " GBi")
    hs("swap_total", str(round(
        psutil.swap_memory().total / GBi, 2)) + " GBi")
    hs("swap_free", str(round(
        psutil.swap_memory().free / GBi, 2)) + " GBi")
    infs = {}
    stats = psutil.net_if_stats()
    for name, inf in psutil.net_if_addrs().items():
        inf_info = {}
        inf_info['address'] = "/".join((str(inf[0].address),
                                        str(inf[0].netmask)))
        inf_info['status'] = 'up' if stats[name].isup else 'down'
        inf_info['mtu'] = stats[name].mtu
        infs[name] = inf_info
    hs("interfaces", infs)
    pids = map(lambda x: x.pid,
               filter(lambda x: 'iscsid' in x.info['name'],
                      psutil.process_iter(attrs=['pid', 'name'])))
    hs("iscsid_pids", pids)
