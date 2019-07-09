from __future__ import (print_function, unicode_literals, division,
                        absolute_import)
"""
This is an example DDCT install plugin.  You would run this plugin by doing

    $ ./ddct install -u example

Which would run the "install" function in this module.  Any other functions
in the module are ignored unless they are called by the "install" function.

Best Practices
--------------
Installs are less regimented than checks or fixes because they are much more
wide ranging in their requirements.

It is advised that you make a "check_requirements" function like below and call
it during install to ensure that all requirements that are required to run
the installer are already available.

The install function can be as simple as calling a binary or external script
or as complex as performing all the necessary file copies and service bringups
that you want.

Installers are not subject to tag filtering, but multiple installers can
be run at the same time by specifying each of them during invocation

    Example:
        $ ./ddct install -u example1 example2

The "config" parameter passed to the "install" function is a UDC dictionary
with 'vip1_ip' key representing the first access VIP on the Datera box
and a potential 'vip2_ip' key which is only present if the Datera box is
configured with a second access VIP.
"""

from common import exe_check, exe, vprint

REQUIREMENTS = ('git', 'curl')


def check_requirements():
    vprint("Checking Requirements")
    for binary in REQUIREMENTS:
        if not exe_check("which {}".format(binary), err=False):
            return "missing " + binary


def install_example(datera_ip):
    exe("cp some_file some_location/")


def install(config):
    reqs = check_requirements()
    if reqs is not None:
        raise ValueError(reqs)
    install_example(config['mgmt_ip'])
