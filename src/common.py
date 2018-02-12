from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import functools
import glob
import importlib
import inspect
import io
import os
import re
import subprocess

try:
    import ipaddress
    import paramiko
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


PLUGIN_LOC = os.path.join(os.path.dirname(__file__), "plugins")
VERBOSE = False
WARNINGS = True

SUCCESS = apply_color("Success", color="green")
FAILURE = apply_color("FAIL", color="red")
WARNING = apply_color("WARN", color="yellow")


CHECK_RE = re.compile(".*check_(.*)\.py")
CHECK_GLOB = "check_*.py"

FIX_RE = re.compile(".*fix_(.*)\.py")
FIX_GLOB = "fix_*.py"

IP_ROUTE_RE = re.compile(
    "^(?P<net>[\w|\.|:|/]+).*dev\s(?P<iface>[\w|\.|:]+).*?$")


class Report(object):

    def __init__(self):
        self.success = []
        self.warning = {}
        self.warning_id = {}
        self.warning_by_id = {}
        self.failure = {}
        self.failure_id = {}
        self.failure_by_id = {}
        self.tags = {}

    def add_success(self, name, tags):
        if name not in self.failure and name not in self.warning:
            self.success.append(name)
            self.tags[name] = tags

    def add_warning(self, name, reason, uid, tags):
        if WARNINGS:
            if name not in self.warning:
                self.warning[name] = []
                self.warning_id[name] = []
            self.warning[name].append(reason)
            self.warning_id[name].append(uid)
            self.warning_by_id[uid] = (name, reason)
            self.tags[name] = tags

    def add_failure(self, name, reason, uid, tags):
        if name not in self.failure:
            self.failure[name] = []
            self.failure_id[name] = []
        self.failure[name].append(reason)
        self.failure_id[name].append(uid)
        self.failure_by_id[uid] = (name, reason)
        self.tags[name] = tags

    def generate(self):
        s = list(map(lambda x: (
            x,
            SUCCESS,
            "",
            "",
            "\n".join(self.tags[x])),
            sorted(self.success)))
        w = list(map(lambda x: (
            x[0],
            WARNING,
            "\n".join(x[1]),
            "\n".join(self.warning_id[x[0]]),
            "\n".join(self.tags[x[0]])),
            sorted(self.warning.items())))
        f = list(map(lambda x: (
            x[0],
            FAILURE,
            "\n".join(x[1]),
            "\n".join(self.failure_id[x[0]]),
            "\n".join(self.tags[x[0]])),
            sorted(self.failure.items())))
        result = tabulate(
            f + w + s,
            headers=["Test", "Status", "Reasons", "IDs", "Tags"],
            tablefmt="grid")
        return result

    def code_list(self):
        result = []
        if WARNINGS:
            result.extend(self.warning_by_id.keys())
        result.extend(self.failure_by_id.keys())
        return result


report = Report()
func_run = set()


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


def plugin_table():
    checks = map(lambda x: [x], check_load())
    fixes = map(lambda x: [x], fix_load())
    print("\n".join((tabulate(checks, headers=["Check Plugins"],
                     tablefmt="grid"),
                     tabulate(fixes, headers=["Fix Plugins"],
                     tablefmt="grid"))))


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
def ff(reasons, uid):
    name, tags = _lookup_vars()
    if type(reasons) not in (list, tuple):
        report.add_failure(name, reasons, uid, tags)
        return
    report.add_failure(name, "\n".join(reasons), uid, tags)


# Warn Func
def wf(reasons, uid):
    name, tags = _lookup_vars()
    if type(reasons) not in (list, tuple):
        report.add_warning(name, reasons, uid, tags)
        return
    report.add_warning(name, "\n".join(reasons), uid, tags)


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
                in_report.add_failure(test, reason, uid, [])
            elif result == WARNING:
                in_report.add_warning(test, reason, uid, [])
            elif result == SUCCESS:
                in_report.add_success(test, [])
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
