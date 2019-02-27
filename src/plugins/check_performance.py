from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

# import io
# import json
# import os


# from dfs_sdk import ApiNotFoundError

from common import vprint, check, exe_check, ff

CONFIG_FILE = "/root/.datera-config-file"


@check("Performance", "plugin", "perf", "fio", "4k")
def check_single_volume_performance_fio_4k(config):
    vprint("Checking FIO performance, single volume")
    if not exe_check("which fio"):
        ff("FIO is not installed", "0BB2848F")
    api = config['api']


def load_checks():
    return [check_single_volume_performance_fio_4k]
