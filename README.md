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
* Cinder Volume Driver (cinder\_volume)
* Glance Driver (glance)
* Kubernetes Flex Driver (k8s\_flex)
* Kubernetes CSI Driver (k8s\_csi)

-------------
Future Checks
-------------

* Cinder Backup Driver
* Glance Image Backend Driver
* Nova Ephemeral Driver
* Docker Driver


-----
Fixes
-----
TBD

-----
Usage
-----

*NOTE*: If running on SUSE Linux Enterprise Server 12 (SLES) you MUST register
the normal SLES repositories as well as the Software Development Kit (SDK)
repositories.

You can check if they are registered with the following:
```
$ zypper refresh
$ zypper lr --show-enabled-only | grep -iE "(enterprise_server|software)" | awk '{print $3}'
SUSE_Linux_Enterprise_Server_12_SP3_x86_64:SLES12-SP3-Debuginfo-Updates
SUSE_Linux_Enterprise_Server_12_SP3_x86_64:SLES12-SP3-Pool
SUSE_Linux_Enterprise_Server_12_SP3_x86_64:SLES12-SP3-Updates
SUSE_Linux_Enterprise_Software_Development_Kit_12_SP3_x86_64:SLE-SDK12-SP3-Debuginfo-Updates
SUSE_Linux_Enterprise_Software_Development_Kit_12_SP3_x86_64:SLE-SDK12-SP3-Pool
SUSE_Linux_Enterprise_Software_Development_Kit_12_SP3_x86_64:SLE-SDK12-SP3-Updates
```

To install DDCT to perform basic readiness checks
```
# Clone the repository
$ git clone http://github.com/Datera/ddct
$ cd ddct

# Installation is currently only supported on Ubuntu/CentOS systems
$ ./install.py
DDCT is now installed.  Use '/home/ubuntu/ddct/ddct' to run DDCT.
The generated config file is located at '/home/ubuntu/ddct/datera-config.json'.
If a universal datera config file should be used, remove the generated config file
```

Edit the generated config file.  Replace the IP addresses and credentials with
those of your Datera EDF cluster

$ vi datera-config.json
```json
{
    "username": "admin",
    "password": "password",
    "tenant": "/root",
    "mgmt_ip": "1.1.1.1",
    "api_version": "2.2"
}
```

Finally, run the tool

```
$ ./ddct check
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
(.ddct) ubuntu@master-xenial-bfd6:~/ddct/src$ ./ddct check
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

---------------
Windows Support
---------------

Currently not all features of DDCT are supported on Windows.  As full Windows
support is being developed, a Powershell script has been added to bridge the
gap.

Copy the powershell script to the local machine.
```powershell
PS C:\> Invoke-WebRequest "https://raw.githubusercontent.com/Datera/ddct/master/src/scripts/check_windows.ps1" -OutFile "C:\Temp\check_windows.ps1"
```

Make sure RemoteSigned is enabled in your Powershell session, otherwise
execution of the script will fail.
```powershell
PS C:\> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

Now run the powershell script (substitute your MGMT IP, VIP1 IP and VIP2 IP)
```powershell
PS C:\> C:\Temp\check_windows.ps1 172.19.1.41 172.28.222.9 172.29.222.9 -human
```
Example Output
```
Checking ISCSI Service
SUCCESS
Testing vip_1 Connection
SUCCESS
Testing vip_2 Connection
SUCCESS
Testing mgmt_ip Connection
SUCCESS
vip_2 was not populated, skipping MTU test
Testing vip_1 MTU
SUCCESS
Testing mgmt_ip MTU
SUCCESS
Checking Power Settings
Power settings are not set to 'High performance'
Checking Recieve Side Scaling
SUCCESS
Finished.  Status Code: 256
FAILED_POWER_SETTINGS
```

Each check will either report SUCCESS or it will display an error at the end
of the test run.

----------
What To Do
----------

Here's a basic scenario where we want to run some checks on a typical L2
deployment with 1 Mgmt and 2 VIPs using the Cinder Volume driver with
multipath.

**NOTE**: currently this tool should be run on each bare-metal host that will
be communicating with the cluster.  In a future release we're looking at adding
the capability for the tool to access additional nodes within the same network
generating a report for each, but this is a ways off.

First we install ddct, this will create an executable for our system and
generate a json file that we can fill out.
```
$ ./install.py
DDCT is now installed.  Use '/opt/stack/ddct/ddct' to run DDCT.
The generated config file is located at '/opt/stack/ddct/datera-config.json'
```

Now we'll edit the generated file and fill out the fields
```
$ vi datera-config.json

{
    "username": "admin",
    "password": "password",
    "tenant": "/root",
    "mgmt_ip": "1.1.1.1",
    "api_version": "2.2"
}
```

The VIP ip addresses will be pulled directly from the cluster.


Once the config file is filled out, we can run a basic set of checks with the
following invocation:
```
$./ddct check

Running checks

Plugins:
Tags:
Not Tags:

+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| Test           | Status   | Reasons                                                                                                                      | IDs      | Tags       |
+================+==========+==============================================================================================================================+==========+============+
| Block Devices  | FAIL     | Scheduler is not set to noop                                                                                                 | 47BB5083 | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| CPUFREQ        | FAIL     | No 'performance' governor found for system.  If this is a VM, governors might not be available and this check can be ignored | 333FBD45 | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| MGMT           | FAIL     | Arp state for mgmt is not 'REACHABLE'                                                                                        | BF6A912A | basic      |
|                |          |                                                                                                                              |          | connection |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| Multipath      | FAIL     | multipathd not enabled                                                                                                       | 541C10BF | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| Multipath Conf | FAIL     | defaults section missing 'checker_timer'                                                                                     | FCFE3444 | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| UDEV           | FAIL     | Datera udev rules are not installed                                                                                          | 1C8F2E07 | basic      |
|                |          | fetch_device_serial_no.sh is missing from /sbin                                                                              | 6D03F50B | udev       |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| VIP1           | FAIL     | Arp state for vip1 is not 'REACHABLE'                                                                                        | 3C33D70D | basic      |
|                |          |                                                                                                                              |          | connection |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| VIP2           | FAIL     | Arp state for vip2 is not 'REACHABLE'                                                                                        | 4F6B8D91 | basic      |
|                |          |                                                                                                                              |          | connection |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| ARP            | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| CONFIG         | Success  |                                                                                                                              |          |            |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| IRQ            | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| ISCSI          | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| OS             | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
```

From the above report we can see that a few things are not configured correctly.
DDCT tries to give a human-readable explatation for each failure so the user
can easily determine what needs to be changed to pass the test.

We won't go through all of what is required to fix the issues above instead
we'll just show a couple of examples.

First we check the OS test.  Because it reported "Success", that means this
Operating System is one currently supported by DDCT.  If this test ever fails,
a ticket/issue should be submitted against DDCT to add support for that OS.

The "Multipath" test failed because multipathd is not enabled.  We can enable
multipathd on a CentOS system by running `systemctl start multipathd &&
systemctl enable multipathd`, but this won't actually solve the problem.  We
can tell from the output before the chart that multipathd is not a recognized
service.  So to fix this we install multipath-tools for our OS.

After fixing any issue, it's a good habit to run the tool again and check
that there are no other issues in that category
```
$./ddct check

Running checks

Plugins:
Tags:
Not Tags:

+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| Test           | Status   | Reasons                                                                                                                      | IDs      | Tags       |
+================+==========+==============================================================================================================================+==========+============+
| Block Devices  | FAIL     | Scheduler is not set to noop                                                                                                 | 47BB5083 | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| CPUFREQ        | FAIL     | No 'performance' governor found for system.  If this is a VM, governors might not be available and this check can be ignored | 333FBD45 | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| MGMT           | FAIL     | Arp state for mgmt is not 'REACHABLE'                                                                                        | BF6A912A | basic      |
|                |          |                                                                                                                              |          | connection |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| Multipath Conf | FAIL     | defaults section missing 'checker_timer'                                                                                     | FCFE3444 | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| UDEV           | FAIL     | Datera udev rules are not installed                                                                                          | 1C8F2E07 | basic      |
|                |          | fetch_device_serial_no.sh is missing from /sbin                                                                              | 6D03F50B | udev       |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| VIP1           | FAIL     | Arp state for vip1 is not 'REACHABLE'                                                                                        | 3C33D70D | basic      |
|                |          |                                                                                                                              |          | connection |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| VIP2           | FAIL     | Arp state for vip2 is not 'REACHABLE'                                                                                        | 4F6B8D91 | basic      |
|                |          |                                                                                                                              |          | connection |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| ARP            | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| CONFIG         | Success  |                                                                                                                              |          |            |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| IRQ            | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| ISCSI          | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| Multipath      | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
| OS             | Success  |                                                                                                                              |          | basic      |
+----------------+----------+------------------------------------------------------------------------------------------------------------------------------+----------+------------+
```

Now we can see that the "Multipath" category is reporting "Success", but the
"Multipath Conf" category still has issues.

Continue addressing issues and re-running the tool until a full clear is
reached.  If for some reason the tool is reporting an error when the reported
issue has been address, please file a bug against DDCT with the following
information:

Category (eg. Multipath)
Operating System (eg. CentOS)
Check Code (eg. 541C10BF)
Actions taken to address issue

so hopefully we can rectify the check or improve the given reasons for failure.

If we want to list the available plugins for DDCT, we can easily do so via
the "--list-plugins" flag.

```
$ ./ddct check --list-plugins
+-----------------+
| Check Plugins   |
+=================+
| performance     |
+-----------------+
| docker          |
+-----------------+
| mtu             |
+-----------------+
| cinder_volume   |
+-----------------+
```

**NOTE**: Not all of the above plugins are available as many are WIP.

Using a plugin is as simple as providing it via the "--use-plugins" flag

```
$ ./ddct check --use-plugin k8s_csi
```


---------------
Writing Plugins
---------------

Creating a plugin for ddct is a straightforward process.

First, determine what the plugin should be called.  For the following
  example, we're going to use the plugin name "my\_driver"

The name you chose determines the name of the two files than need to be created
under src/plugins, a check file (check\_my\_driver.py) and a fix file
(fix\_my\_driver.py)

The Check file will always have the format "check_$(your_name).py"

The Fix file will always have the format "fix_$(your_name).py"

Once we've placed these two files under src/plugins, add the following template
to the check file (check\_my\_driver.py)
```python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

from common import vprint, exe_check, ff, wf, check

def load_checks():
    return []
```

* Add the next template to the fix file (fix\_my\_driver.py)
```python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)
from common import vprint, exe

def load_fixes():
    return {}
```

All checks your plugin should run should be returned as a list by the
"load\_checks" function.  The "load\_checks" function takes no parameters, but
each test function should take a "config" parameter which consists of the
dictionary below:
```json
{
    "mgmt_ip": "172.19.1.41",
    "password": "password",
    "username": "admin"
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
@check("MY TESTS", "basic")
def my_plugin_tests(config):
    if not exe_check("which ping", err=False):
        return ff("Couldn't find ping", "95C9B3AC")
```

This would be shown in the report as the following line:
```
+----------+------+----------------------+----------+--------+
| MY TESTS | FAIL | Couldn't find ping   | 95C9B3AC | basic  |
+----------+------+----------------------+----------+--------+
```
The `@check` decorator's first argument is the name/category of the test and
every argument afterwards is a "tag" that can be used for selecting and
deselecting this test with the `--tags` and `--not-tags` flags respectively.
In the case of the above test `--tags basic` would select the test for running
(as well as any other test with the "basic" tag).  Then you could deselect the
test with `--not-tags basic` and no tests with the "basic" flag would be run.
Any number of tags may be given to a test.


When writing fixes, we associate the test ID with a fix.  Below is an example
of a fix and the entry it makes in "load\_fixes()":
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
and import a function from common called "no\_fix" like the example below:
```python
def load_fixes():
    return {"95C9B3AC": [my_ping_fix_1, my_ping_fix_2],
            "8A28D615": [no_fix]}
```

This allows the print\_fixes function to show in the output that this code has
no fix.

Now that we're all done with "my\_driver" checks and fixes, we can load them
via the following:
```bash
$ ./ddct check --use-plugin my_driver
```
