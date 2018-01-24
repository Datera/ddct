#############################################
## The Datera Deployment Check Tool (DDCT) ##
#############################################

-------
Purpose
-------
This tool is designed to be run on customer systems as an easy way to determine
if they are currently configured correctly (by the standards of the tool) for
starting a set of PoC tests.

------
Checks
------

* ARP
* IRQ
* CPU Frequency
* Block Devices
* Multipath
* Cinder Volume Driver

-------------
Future Checks
-------------

* Cinder Backup Driver
* Glance Image Backend Driver
* Nova Ephemeral Driver
* Docker Driver
* Kubernetes Driver


-----
Fixes
-----
TBD

-----
Usage
-----

To perform basic readiness checks:

```
# Clone the repository
$ git clone http://github.com/Datera/ddct
$ cd ddct/src

# Create workspace
$ virtualenv .ddct
$ source .ddct/bin/activate

# Install requirements
$ pip install -r ../requirements.txt

# Generate config file
$ ./ddct.py -g

# Edit config file.  Replace the IP addresses and credentials with those of
# your Datera EDF cluster
$ vi ddct.json
{
    "cinder-volume": {
        "location": null,
        "version": "v2.7.2"
    },
    "mgmt_ip": "172.19.1.41",
    "password": "password",
    "username": "admin",
    "vip1_ip": "172.28.41.9",
    "vip2_ip": "172.29.41.9"
}

# Finally, run the tool
$ ./ddct.py -c ddct.json
```

The report will have the following format:

```
+-------+--------+---------+-----+
| Test  | Status | Reasons | IDs |
+=======+========+=========+=====+
```

Where "Test" is the test category, "Status" is Success, FAIL or WARN, "Reasons"
are the human readable failure conditions meant to give the user an idea of
what needs to be fixed to pass the test and "IDs" are the unique codes associated
with each test for use by the fixer to run specific fixes for each.

Below is an example output.  Tests with multiple failure conditions will have
all currently check-able reasons listed.
```
(.ddct) ubuntu@master-xenial-bfd6:~/ddct/src$ ./ddct.py -c ddct.json
Running checks
+----------------+----------+----------------------------------------------------------------------------------+----------+
| Test           | Status   | Reasons                                                                          | IDs      |
+================+==========+==================================================================================+==========+
| ARP            | FAIL     | net.ipv4.conf.all.arp_announce != 2 in sysctl                                    | 9000C3B6 |
|                |          | net.ipv4.conf.all.arp_ignore != 1 in sysctl                                      | BDB4D5D8 |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| Block Devices  | FAIL     | Scheduler is not set to noop                                                     | 47BB5083 |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| CPUFREQ        | FAIL     | cpupower is not installed                                                        | 20CEE732 |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| Cinder Volume  | FAIL     | datera is not set under enabled_backends in /etc/cinder/cinder.conf              | A4402034 |
|                |          | san_ip line is missing or not matching ip address: 172.19.1.41                   | 8208B9E7 |
|                |          | san_login line is missing or not matching username: admin                        | 3A6A78D1 |
|                |          | san_password line is missing or not matching password: password                  | 8DBC87E8 |
|                |          | volume_backend_name is not set                                                   | 5FEC0454 |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| IRQ            | FAIL     | irqbalance is active                                                             | B19D9FF1 |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| Multipath      | FAIL     | Multipath binary could not be found, is it installed?                            | 2D18685C |
|                |          | multipathd not enabled                                                           | 541C10BF |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| Multipath Conf | FAIL     | Missing defaults section                                                         | 1D8C438C |
|                |          | Missing devices section                                                          | 797A6031 |
|                |          | Missing blacklist_exceptions section                                             | B8C8A19C |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| VIP2           | FAIL     | Could not ping vip2 ip 172.29.41.9                                               | 3D76CE5A |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| Cinder Volume  | WARN     | datera is not set as default_volume_type in /etc/cinder/cinder.conf              | C2B8C696 |
|                |          | datera_volume_type_defaults is not set, consider setting minimum QoS values here | B5D29621 |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| CONFIG         | Success  |                                                                                  |          |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| MGMT           | Success  |                                                                                  |          |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| OS             | Success  |                                                                                  |          |
+----------------+----------+----------------------------------------------------------------------------------+----------+
| VIP1           | Success  |                                                                                  |          |
+----------------+----------+----------------------------------------------------------------------------------+----------+
```

This report can then be fed back into the tool via the following invocation:

```
$ ./ddct.py -c ddct.json -i test-output.txt -f
```
The -i flag lets you specify a file which has a report like the one above and
the -f flag indicates that the tool should run fixes based on the report output

If a particular fix should NOT be run, then simply delete the line with its ID
in the report.

Each fix will only be run one time per tool invocation.  This ensures that
fixes can be written in a non-idempotent style.

The tool should be run until all checks show "Success"

---------------
Writing Plugins
---------------

Creating a plugin for ddct is a straightforward process and can be accomplished
via the following steps:

* First, determine what the plugin should be called.  For the following
  example, we're going to use the plugin name "my_driver"
* The name you chose determines the name of the two files than need to be
  created under src/plugins, a check file (check_my_driver.py) and a fix file
  (fix_my_driver.py)
* The Check file will always have the format "check_$(your_name).py"
* The Fix file will always have the format "fix_$(your_name).py"
* Once we've placed these two files under src/plugins, add the following
  template to the check file (check_my_driver.py)
```python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

from common import vprint, exe_check, ff, wf, check

def run_checks(config):
    pass
```

* Add the next template to the fix file (fix_my_driver.py)
```python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)
from common import vprint, exe

def load_fixes():
    return {}
```

All checks your plugin should run should be called by the "run_checks" function.
The function has takes a "config" parameter which will be the contents of the
ddct config an example of which can be seen here:
```json
{
    "cinder-volume": {
        "location": null,
        "version": "v2.7.2"
    },
    "mgmt_ip": "172.19.1.41",
    "password": "password",
    "username": "admin",
    "vip1_ip": "172.28.41.9",
    "vip2_ip": "172.29.41.9"
}
```

When writing a check, the following functions should be used to denote warning
and failure and are imported from common:

Warning: wf(reason, id)
Failure: ff(reason, id)

Where "reason" is the human readable reason for test failure (or warning) and
"id" is the manually created unique ID for the failure.  A test that returns
without calling "wf" or "ff" is considered a "success".

IDs can be created by taking the first section of a UUID4 ID and uppercasing it.
In python this can be accomplished via
```python
import uuid

print(str(uuid.uuid4()).split(-)[0])
```
I've also created a handy VIM shortcut for this:
```viml
nnoremap <Leader>u mm:r!uuidgen\|cut -c 1-8<CR>dW"_dd`mi""<Esc>hp
```

These IDs should never be changed after creation (other than check deletion)
as they are used for determining the series of fixes needed.

Below is an example test case:

```python
@check("MY TESTS")
def my_plugin_tests():
    if not exe_check("which ping", err=False):
        return ff("Couldn't find ping", "95C9B3AC")
```

This would be shown in the report as the following line:
```
+----------+------+----------------------+----------+
| MY TESTS | FAIL | Couldn't find ping   | 95C9B3AC |
+----------+------+----------------------+----------+
```

When writing fixes, we associate the test ID with a fix.  Below is an example
of a fix and the entry it makes in "load_fixes()":
```python
def my_ping_fix(config):
    vprint("Fixing missing ping")
    exe("do stuff")

def load_fixes():
    return {"95C9B3AC": [my_ping_fix]}
```

If the above was a multi-step fix (with independent steps) you could do the
following:
```python
def my_ping_fix_1(config):
    vprint("Fixing missing ping")
    exe("do stuff")

def my_ping_fix_2(config):
    vprint("Trying another thing to fix ping")
    exe("do other stuff")

def load_fixes():
    return {"95C9B3AC": [my_ping_fix_1, my_ping_fix_2]}
```

Each fix function will be executed in order.  Fix functions can have either no
arguments, or accept "config" as the sole argument

If you have a check that has no viable fix, you can put it in the fix file
and import a function from common called "no_fix" like the example below:
```python
def load_fixes():
    return {"95C9B3AC": [my_ping_fix_1, my_ping_fix_2],
            "8A28D615": [no_fix]}
```

This allows the print_fixes function to show in the output that this code has
no fix.

Now that we're all done with "my_driver" checks and fixes, we can load them
via the following:
```bash
$ ./ddct.py -c ddct.json --use-plugin my_driver
```
