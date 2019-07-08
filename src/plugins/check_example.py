from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

"""
This is an example DDCT plugin.  You would run this plugin by doing

    $./ddct check -u example

Which would run the following additional tests:
    * check_something
    * check_something_else

Abbreviations:
    "ff" --> Failure Function
    "wf" --> Warning Funciton

Best Practices
--------------
You can add as many separate test functions as you want, but all of them
MUST be added to the "load_checks" function return and all of them MUST be
decorated with the @check decorator function.

It's recommended to exit on the first failure that prevents further checks
from completing.  This is to prevent red-herring errors down the line that
occur because a previous check failed from filling the report output.

    Example:
        @check("MY TEST", "mytag")
        def check_stuff(config):
            if not my_test_that_can_fail_without_affecting_future_tests():
                ff("This is a failure, but we can keep going")
            if not my_test_that_NEEDS_to_pass():
                ff("This is a dealbreaker")
                # This return keeps the last check in this function
                # from running
                return
            if not my_last_test():
                ff("The last test failed")


Try to make your failure messages as direct as possible.  Assume your user can
read adequately, but might lack the technical capability to think critically
about the error message.  You can provide a "fix" field to the "ff" function
that gives the user a direct order for what to change to make this error go
away.

    Example:
        if not my_test_that_should_pass():
            ff("This test failed for this reason",
               fix="Copy {this file} to {this-location} to fix it")

Use "wf" to indicate that something isn't quite ideal, but not a show-stopper.

Every @check decorated function will show as a "success" in the report if
"ff" or "wf" is never called by the time it returns.

The first argument to the @check decorator is the "class" of test.  All tests
sharing the same "class" string will show up under the same section of the
report.  Every argument after the first argument is a "tag" string.  These
are used for filtering tests.  For example, you can use the tag "network" to
ensure this test is affected by filters like the following:

    # Run only tests with the "network" tag
    $ ./ddct check --tags network

    Or

    # Run only tests without the "network" tag
    $ ./ddct check --not-tags network
"""

from common import exe_check, exe, wf, ff, check


@check("MY EXAMPLE PLUGIN", "tag1", "tag2")
def check_something(config):
    if not exe_check("ping -C 2 -W 1 1.1.1.1"):
        ff("This test failed")
        return
    if not exe_check("traceroute 1.1.1.1"):
        wf("This is a warning")


@check("MY EXAMPLE PLUGIN", "tag1", "tag3")
def check_something_else(config):
    out = exe("cat somefile")
    if "something I care about" not in out:
        ff("This test failed")


def load_checks():
    return [check_something,
            check_something_else]
