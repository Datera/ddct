from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import subprocess

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


def apply_color(value_for_coloring=None, color=None):
    suffix = "\x1b[0m"
    if color == "red":
        prefix = "\x1b[31m"
    elif color == "green":
        prefix = "\x1b[32m"
    elif color == "yellow":
        prefix = "\x1b[33m"
    elif color == "cyan":
        prefix = "\x1b[36m"
    return "{}{}{}".format(prefix, value_for_coloring, suffix)


VERBOSE = False
WARNINGS = True

SUCCESS = apply_color("Success", color="green")
FAILURE = apply_color("FAIL", color="red")
WARNING = apply_color("WARN", color="yellow")


class Report(object):

    def __init__(self):
        self.success = []
        self.warning = {}
        self.warning_id = {}
        self.warning_by_id = {}
        self.failure = {}
        self.failure_id = {}
        self.failure_by_id = {}

    def add_success(self, name):
        if name not in self.failure and name not in self.warning:
            self.success.append(name)

    def add_warning(self, name, reason, uid):
        if WARNINGS:
            if name not in self.warning:
                self.warning[name] = []
                self.warning_id[name] = []
            self.warning[name].append(reason)
            self.warning_id[name].append(uid)
            self.warning_by_id[uid] = (name, reason)

    def add_failure(self, name, reason, uid):
        if name not in self.failure:
            self.failure[name] = []
            self.failure_id[name] = []
        self.failure[name].append(reason)
        self.failure_id[name].append(uid)
        self.failure_by_id[uid] = (name, reason)

    def generate(self):
        s = list(map(lambda x: (x, SUCCESS, ""), sorted(self.success)))
        w = list(map(lambda x: (
            x[0],
            WARNING,
            "\n".join(x[1]),
            "\n".join(self.warning_id[x[0]])),
            sorted(self.warning.items())))
        f = list(map(lambda x: (
            x[0],
            FAILURE,
            "\n".join(x[1]),
            "\n".join(self.failure_id[x[0]])),
            sorted(self.failure.items())))
        result = tabulate(
            f + w + s,
            headers=["Test", "Status", "Reasons", "IDs"],
            tablefmt="grid")
        return result


report = Report()


def parse_mconf(data):

    def _helper(lines):
        result = []
        for line in lines:
            line = line.strip()
            line = line.split()
            if not line or len(line) < 1 or line[0].startswith("#"):
                continue
            elif line[-1] == "{":
                result.append([line[0], _helper(lines)])
                continue
            elif line[-1] == "}":
                break
            result.append([line[0], " ".join(line[1:]).strip("\"'")])
        return result

    return _helper(iter(data.splitlines()))


# Success Func
def sf(name):
    report.add_success(name)


# Fail Func
def ff(name, reasons, uid):
    if type(reasons) not in (list, tuple):
        report.add_failure(name, reasons, uid)
        return
    report.add_failure(name, "\n".join(reasons), uid)


# Warn Func
def wf(name, reasons, uid):
    if type(reasons) not in (list, tuple):
        report.add_warning(name, reasons, uid)
        return
    report.add_warning(name, "\n".join(reasons), uid)


def gen_report(outfile=None, quiet=False):
    results = report.generate()
    if outfile:
        with io.open(outfile, 'w+') as f:
            f.write(results)
            f.write("\n")
    if not quiet:
        print(results)


def read_report(infile):
    in_report = Report()
    with io.open(infile, 'r') as f:
        header_skip = True
        prevr = None
        prevt = None
        for line in f:
            if "|" not in line:
                continue
            elif header_skip:
                header_skip = False
                continue
            test, result, reason, uid = list(
                map(lambda x: x.strip(), line.split("|")))[1:-1]
            if result == "":
                result = prevr
                test = prevt
            if result == FAILURE:
                in_report.add_failure(test, reason, uid)
            elif result == WARNING:
                in_report.add_warning(test, reason, uid)
            elif result == SUCCESS:
                in_report.add_success(test)
            prevr = result
            prevt = test
    return in_report


def vprint(*args, **kwargs):
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
