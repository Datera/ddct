from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import threading

install_list = []


def load_plugin_installers(plugins):
    install_list.extend()


def load_checks(config, plugins=None, tags=None, not_tags=None):
    if plugins:
        load_plugin_installers(plugins)
    threads = []

    # Filter checks to be executed based on tags passed in
    checks = install_list
    if tags:
        checks = filter(lambda x: any([t in x._tags for t in tags]),
                        checks)
    if not_tags:
        checks = filter(lambda x: not any([t in x._tags for t in not_tags]),
                        checks)
    for ck in checks:
        thread = threading.Thread(target=ck, args=(config,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()


def print_tags(config, plugins=None):
    if plugins:
        load_plugin_installers(plugins)
    tags = set()
    for install in install_list:
        for tag in install._tags:
            tags.add(tag)
    print("\nTags")
    print("----")
    print("\n".join(sorted(tags)))
    print()

# Possible additional checks
# ethtool -S
# netstat -F (retrans)
