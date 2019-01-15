from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import sys

from common import install_load

install_list = []


def load_plugin_installers(plugins):
    plugs = install_load()
    for plugin in plugins:
        if plugin not in plugs:
            print("Unrecognized install plugin requested:", plugin)
            print("Available install plugins:", ", ".join(plugins.keys()))
            sys.exit(1)
        install_list.append(plugs[plugin].install)


def run_installers(config, plugins):
    results = []
    load_plugin_installers(plugins)
    for installer in install_list:
        results.append(installer(config))
