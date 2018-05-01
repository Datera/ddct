from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import functools
import glob
import importlib
import inspect
import io
import json
import os
import re
import subprocess
import socket
import textwrap

try:
    import ipaddress
    import paramiko
    import requests
    from tabulate import tabulate
except ImportError:
    ipaddress = None
    tabulate = None
    paramiko = None

# Python 2/3 compatibility
try:
    str = unicode
except NameError:
    pass

TAG_RE = re.compile("\d+\.\d+\.\d+")
UUID4_STR_RE = re.compile("[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab]"
                          "[a-f0-9]{3}-?[a-f0-9]{12}")

INVISIBLE = re.compile(r"\x1b\[\d+[;\d]*m|\x1b\[\d*\;\d*\;\d*m")


def get_latest_driver_version(tag_url):
    found = []
    weighted_found = []
    tags = requests.get(tag_url).json()
    for tag in tags:
        tag = tag['name'].strip("v")
        if TAG_RE.match(tag):
            found.append(tag)
    for f in found:
        # Major, minor, patch
        try:
            # Version format: M.m.p
            M, m, p = f.split(".")
            value = int(M) * 10000 + int(m) * 100 + int(p)
        except ValueError:
            # Date format: YYYY.M.d.n
            Y, M, d, n = f.split(".")
            value = int(Y) * 1000000 + int(M) * 10000 + int(d) * 100 + int(n)
        weighted_found.append((value, "v" + f))
    return sorted(weighted_found)[-1][1]


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
    elif color == "magenta":
        prefix = "\x1b[35m"
    return "{}{}{}".format(prefix, value_for_coloring, suffix)


def strip_invisible(s):
    return re.sub(INVISIBLE, "", s)


PLUGIN_LOC = os.path.join(os.path.dirname(__file__), "plugins")
VERBOSE = False
WARNINGS = True
WRAPTXT = True


SUCCESS = apply_color("Success", color="green")
FAILURE = apply_color("FAIL", color="red")
WARNING = apply_color("WARN", color="yellow")
# FIX = apply_color("FIX {}", color="cyan")
FIX = "FIX {}"
# ISSUE = apply_color("ISSUE {}", color="magenta")
ISSUE = "ISSUE {}"


CHECK_RE = re.compile(".*check_(.*)\.py")
CHECK_GLOB = "check_*.py"

FIX_RE = re.compile(".*fix_(.*)\.py")
FIX_GLOB = "fix_*.py"

INSTALL_RE = re.compile(".*install_(.*)\.py")
INSTALL_GLOB = "install_*.py"

IP_ROUTE_RE = re.compile(
    "^(?P<net>[\w|\.|:|/]+).*dev\s(?P<iface>[\w|\.|:]+).*?$")


def _wraptxt(txt, fill):
    if WRAPTXT:
        return textwrap.fill(txt, fill)
    return txt


class Report(object):

    def __init__(self):
        self.hostname = None
        self.success = []
        self.warning = {}
        self.warning_id = {}
        self.warning_by_id = {}
        self.fix_by_id = {}
        self.failure = {}
        self.failure_id = {}
        self.failure_by_id = {}
        self.tags = {}

    @staticmethod
    def format_fix(fix, uid):
        # return "{}: {}".format(FIX, apply_color(fix, "magenta"))
        return "{}: {}".format(FIX, fix).format(uid)

    @staticmethod
    def format_issue(issue, uid):
        return "{}: {}".format(ISSUE, issue).format(uid)

    def add_success(self, name, tags):
        if name not in self.failure and name not in self.warning:
            self.success.append(name)
            if name not in tags:
                self.tags[name] = set()
            for tag in tags:
                self.tags[name].add(tag)

    def add_warning(self, name, reason, uid, tags, fix=None):
        reason = self.format_issue(reason, uid)
        if WARNINGS:
            if name not in self.warning:
                self.warning[name] = []
                self.warning_id[name] = []
            self.warning[name].append(reason)
            self.warning_id[name].append(uid)
            self.warning_by_id[uid] = (name, reason)
            if fix:
                self.fix_by_id[uid] = self.format_fix(fix, uid)
            if name not in tags:
                self.tags[name] = set()
            for tag in tags:
                self.tags[name].add(tag)

    def add_failure(self, name, reason, uid, tags, fix=None):
        reason = self.format_issue(reason, uid)
        if name not in self.failure:
            self.failure[name] = []
            self.failure_id[name] = []
        self.failure[name].append(reason)
        self.failure_id[name].append(uid)
        self.failure_by_id[uid] = (name, reason)
        if fix:
            self.fix_by_id[uid] = self.format_fix(fix, uid)
        if name not in tags:
            self.tags[name] = set()
        for tag in tags:
            self.tags[name].add(tag)

    def generate(self):
        if not self.hostname:
            self.hostname = socket.gethostname()
        try:
            longest = max(map(
                lambda x: len(x),
                [val for sublist in
                    list(self.failure.values()) + list(self.warning.values())
                    for val in sublist]))
        except ValueError:
            longest = 30
        s = list(map(lambda x: (
            x,
            SUCCESS,
            "",
            "",
            "\n".join(sorted(self.tags[x]))),
            sorted(self.success)))

        w = []
        for name, wids in self.warning_id.items():
            warnings = []
            nwids = []
            for wid in wids:
                nwids.append(wid)
                warnings.append(self.warning_by_id[wid][1])
                fix = self.fix_by_id.get(wid)
                if fix:
                    nwids.append("\n")
                    warnings.append(fix)
            for index, warning in enumerate(warnings):
                if "FIX" in warning:
                    warnings[index] = _wraptxt(warning, longest) + "\n"
            w.append([name,
                      WARNING,
                      "\n".join(warnings),
                      "\n".join(sorted(self.tags[name]))])
        f = []
        for name, fids in self.failure_id.items():
            failures = []
            nfids = []
            for fid in fids:
                nfids.append(fid)
                failures.append(self.failure_by_id[fid][1])
                fix = self.fix_by_id.get(fid)
                if fix:
                    failures.append(fix)
            for index, failure in enumerate(failures):
                if "FIX" in failure:
                    failures[index] = _wraptxt(failure, longest) + "\n"
            f.append([name,
                      FAILURE,
                      "\n".join(failures),
                      "\n".join(sorted(self.tags[name]))])

        result = tabulate(
            f + w + s,
            headers=["Test", "Status", "Reasons", "Tags"],
            tablefmt="grid")
        result = "\n".join(("HOST: {}".format(self.hostname), result))
        return result

    def gen_json(self):
        if not self.hostname:
            self.hostname = socket.gethostname()
        return {"host": self.hostname,
                "success": self.success,
                "warnings": self.warning_by_id,
                "failures": self.failure_by_id}

    def code_list(self):
        result = []
        if WARNINGS:
            result.extend(self.warning_by_id.keys())
        result.extend(self.failure_by_id.keys())
        print(result)
        return result


report = Report()
func_run = set()


def reset_checks():
    global report
    report = Report()


def idempotent(func):
    if func.__name__ in func_run:
        return
    func_run.add(func.__name__)

    @functools.wraps(func)
    def _wrapper():
        func()

    return _wrapper


def check(test_name, *tags):
    """
    Decorator to be used for checks that automatically calls sf() at the
    end of the check.

    NOTE: This should always be the outermost decorator due to
          non-kosher behavior that *should* make our lives easier

    Usage:
        @check("Test Name")
        def my_tests():
            if not some_condition:
                ff("We failed!")


    Which is equivalent to:
        def my_tests():
            name = "Test Name"
            if not some_condition:
                ff(name, "We Failed!")
            sf(name)
    """
    def _outer(func):
        @functools.wraps(func)
        def _inner_check_func(*args, **kwargs):
            tname = test_name  # noqa
            ttags = tags  # noqa
            result = func(*args, **kwargs)
            sf()
            return result
        _inner_check_func._tags = tags
        return _inner_check_func
    return _outer


def load_plugins(regex, globx):
    found = {}
    RE = re.compile(regex)
    path = glob.glob(os.path.join(PLUGIN_LOC, globx))
    for file in path:
        name = RE.match(file).groups(1)[0]
        mod = importlib.import_module("plugins." + os.path.basename(file)[:-3])
        found[name] = mod
    return found


def check_load():
    return load_plugins(CHECK_RE, CHECK_GLOB)


def fix_load():
    return load_plugins(FIX_RE, FIX_GLOB)


def install_load():
    return load_plugins(INSTALL_RE, INSTALL_GLOB)


def check_plugin_table():
    checks = map(lambda x: [x], check_load())
    print(tabulate(checks, headers=["Check Plugins"], tablefmt="grid"))


def fix_plugin_table():
    fixes = map(lambda x: [x], fix_load())
    print(tabulate(fixes, headers=["Fix Plugins"], tablefmt="grid"))


def install_plugin_table():
    installs = map(lambda x: [x], install_load())
    print(tabulate(installs, headers=["Install Plugins"], tablefmt="grid"))


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


def get_os():
    if exe_check("which apt-get > /dev/null 2>&1", err=False):
        return "ubuntu"
    if exe_check("which yum > /dev/null 2>&1", err=False):
        return "centos"


def _lookup_vars():
    name = None
    for frame in inspect.stack():
        if frame[3] == "_inner_check_func":
            name = frame[0].f_locals['test_name']
            tags = frame[0].f_locals['tags']
            break
    if not name:
        raise ValueError("Couldn't find test_name in frame stack")
    return name, tags


# Success Func
def sf():
    name, tags = _lookup_vars()
    report.add_success(name, tags)


# Fail Func
def ff(reasons, uid, fix=None):
    name, tags = _lookup_vars()
    if type(reasons) not in (list, tuple):
        report.add_failure(name, reasons, uid, tags, fix=fix)
        return
    report.add_failure(name, "\n".join(reasons), uid, tags, fix=fix)


# Warn Func
def wf(reasons, uid, fix=None):
    name, tags = _lookup_vars()
    if type(reasons) not in (list, tuple):
        report.add_warning(name, reasons, uid, tags, fix=fix)
        return
    report.add_warning(name, "\n".join(reasons), uid, tags, fix=fix)


def gen_report(outfile=None, quiet=False, ojson=False):
    if ojson:
        results = report.gen_json()
    else:
        results = report.generate()
    if outfile:
        try:
            with io.open(outfile, 'w+') as f:
                f.write(results)
                f.write("\n")
        except TypeError:
            outfile.write(results)
            outfile.write("\n")
    if ojson and not quiet:
        print(json.dumps(results, indent=4))
    elif not quiet:
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
            test, result, reason, uid, tags = list(
                map(lambda x: x.strip(), line.split("|")))[1:-1]
            print(test, result, reason, uid, tags, sep=", ")
            if result == "":
                result = prevr
                test = prevt
            if result == FAILURE:
                in_report.add_failure(test, reason, uid, tags.split())
            elif result == WARNING:
                in_report.add_warning(test, reason, uid, tags.split())
            elif result == SUCCESS:
                in_report.add_success(test, tags.split())
            prevr = result
            prevt = test
    return in_report


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def exe(cmd):
    vprint("Running cmd:", cmd)
    return subprocess.check_output(cmd, shell=True).decode("utf-8")


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


def cluster_cmd(cmd, config, fail_ok=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy())
    if config.get('cluster_root_keyfile'):
        ssh.connect(hostname=config['mgmt_ip'],
                    username='root',
                    banner_timeout=60,
                    pkey=config.get('cluster_root_keyfile'))
    elif config.get('cluster_root_password'):
        ssh.connect(hostname=config['mgmt_ip'],
                    username='root',
                    password=config.get('cluster_root_password'),
                    banner_timeout=60)
    else:
        raise ValueError("Missing cluster_root_keyfile or "
                         "cluster_root_password for this test")
    msg = "Executing command: {} on Cluster".format(cmd)
    vprint(msg)
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    result = None
    if int(exit_status) == 0:
        result = stdout.read()
    elif fail_ok:
        result = stderr.read()
    else:
        raise EnvironmentError(
            "Nonzero return code: {} stderr: {}".format(
                exit_status,
                stderr.read()))
    return result


def is_l3(config):
    api = config['api']
    return api.system.get()['l3_enabled']


def parse_route_table():
    results = []
    data = exe("ip route show")
    for line in data.splitlines():
        match = IP_ROUTE_RE.match(line)
        if match:
            try:
                net = ipaddress.ip_network(str(match.group("net")))
            except ValueError:
                continue
            results.append((net, match.group("iface")))
    return results
