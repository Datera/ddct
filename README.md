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
