from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import subprocess

from tabulate import tabulate

VERBOSE = False
SUCCESS = "{} : Success"
WARNING = "{} : WARN --"
FAILURE = "{} : FAIL --"


class Report(object):

    def __init__(self):
        self.success = []
        self.warning = []
        self.failure = []

    def add_success(self, name):
        self.success.append(name)

    def add_warning(self, name, reason):
        self.warning.append((name, reason))

    def add_failure(self, name, reason):
        self.failure.append((name, reason))

    def generate(self):
        s = list(map(lambda x: (x, "Success", ""), self.success))
        w = list(map(lambda x: (x[0], "WARN", x[1]), self.warning))
        f = list(map(lambda x: (x[0], "FAIL", x[1]), self.failure))
        result = tabulate(
            f + w + s,
            headers=["Test", "Status", "Reasons"],
            tablefmt="grid")
        return result


report = Report()


# Success Func
def sf(name):
    report.add_success(name)


# Fail Func
def ff(name, reasons):
    if type(reasons) not in (list, tuple):
        report.add_failure(name, reasons)
        return
    report.add_failure(name, "\n".join(reasons))


# Warn Func
def wf(name, reasons):
    if type(reasons) not in (list, tuple):
        report.add_warning(name, reasons)
        return
    report.add_warning(name, "\n".join(reasons))


def gen_report():
    print(report.generate())


def vprint(*args, **kwargs):
    global VERBOSE
    if VERBOSE:
        print(*args, **kwargs)


def exe(cmd):
    vprint("Running cmd:", cmd)
    return subprocess.check_output(cmd, shell=True)


def exe_check(cmd, err=False):
    try:
        exe(cmd)
        if err:
            return False
        return True
    except subprocess.CalledProcessError:
        if not err:
            return False
        return True
