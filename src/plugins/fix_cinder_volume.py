from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import os

# from common import vprint, exe, exe_check
from fixers import no_fix
# from plugins.check_cinder_volume import ETC, detect_cinder_install

REQUIREMENTS = ('git', 'curl')
DEVSTACK_INSTALL = "/opt/stack/cinder/cinder"
GITHUB = "http://github.com/Datera/cinder-driver"
HOME = os.path.expanduser("~")
REPO = "{}/cinder-driver".format(HOME)
ETC_TEMPLATE = """
[datera]
volume_driver = cinder.volume.drivers.datera.datera_iscsi.DateraDriver
san_is_local = True
san_ip = {ip}
san_login = {login}
san_password = {password}
volume_backend_name = datera
datera_debug = True
"""


def load_fixes():
    return {
        "680E61DB": [no_fix],
        "A37FD778": [no_fix],
        "5B6EFC71": [no_fix],
        "A4402034": [no_fix]}
