from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import json
import os


from dfs_sdk import ApiNotFoundError

from common import vprint, exe, exe_check, wf, ff, check

CONFIG_FILE = "/root/.datera-config-file"
PLUGIN = "dateraiodev/docker-driver"


@check("Docker Volume", "driver", "plugin", "local")
def check_docker_volume(config):
    vprint("Checking docker volume driver")
    if not exe_check("docker ps >/dev/null 2>&1"):
        return ff("Docker is not installed", "42BAAC76")
    if exe_check("docker plugin ls | grep {}".format(PLUGIN)):
        return ff("Datera Docker plugin is not installed", "6C531C5D")
    plugin = exe("docker plugin ls | grev -v DESCRIPTION | "
                 "grep {}".format(PLUGIN))
    if len(plugin.strip().split('\n')) > 1:
        wf("More than one version of Datera docker driver installed",
           "B3BF691D")
    if 'enabled' not in plugin or 'disabled' in plugin:
        ff("Datera docker plugin is not enabled")
    test_name = "ddct-test1"
    if not exe_check(
            "docker volume create -d {} --name {} --opt replica=1 --opt "
            "size=1".format(PLUGIN, test_name)):
        return ff("Could not create a volume with the Datera Docker plugin",
                  "621A6F51")
    api = config['api']
    try:
        api.app_instances.get(test_name)
    except ApiNotFoundError:
        return ff("Docker volume {} did not create on the Datera backend"
                  "".format(test_name), "B106D1CD")
    if not exe_check("docker volume rm {}".format(test_name)):
        ff("Could not delete Docker volume {}".format(test_name), "AF3DB8B3")


@check("Docker Volume Config", "driver", "plugin", "local")
def check_docker_config(config):
    if not os.path.exists(CONFIG_FILE):
        return ff("Missing Datera config file at '/root/.datera-config-file'",
                  "A433E6C6")
    dconfig = None
    with io.open(CONFIG_FILE) as f:
        try:
            dconfig = json.loads(f.read())
        except json.JSONDecodeError:
            return ff("Malformed config file, not valid JSON", "AA27965F")
    for key in ("datera-cluster", "username", "password", "debug", "os-user",
                "tenant"):
        if key not in dconfig:
            ff("Config missing {} key".format(key), "945148B0")


def load_checks():
    return [check_docker_volume,
            check_docker_config]
