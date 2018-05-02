from __future__ import (print_function, unicode_literals, division,
                        absolute_import)


import curses
import datetime
import StringIO
import time

import common

from checkers import load_checks
from common import gen_report

INVISIBLE = 0
VISIBLE = 1

GREEN = 1
RED = 2
CYAN = 3
YELLOW = 4
BLACK = 5
WHITE = 6
MAGENTA = 7


class WinWrap(object):
    def __init__(self, win, x, y):
        self.win = win
        self.xbase = x
        self.ybase = y
        self.x = x
        self.y = y

    def addstr(self, y, x, s, color=0):
        self.x = x
        self.y = y
        self.win.addstr(self.y, self.x, s, color)

    def addsameln(self, s, color=0):
        self.win.addstr(self.y, self.x, s, color)
        self.x += len(s)

    def endln(self):
        self.x = self.xbase
        self.y += 1

    def addln(self, s, color=0):
        self.win.addstr(self.y, self.x, s, color)
        self.y += 1
        self.x = self.xbase

    def refresh(self, *args):
        self.win.refresh(*args)
        self.x = self.xbase
        self.y = self.ybase

    def clear(self):
        self.win.clear()
        self.x = self.xbase
        self.y = self.ybase

    def clrtoeol(self):
        self.win.clrtoeol()

    def getch(self):
        return self.win.getch()


def daemon(stdscr, config, args):
    curses.curs_set(INVISIBLE)
    curses.start_color()
    curses.init_pair(GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(RED, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(CYAN, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(MAGENTA, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(BLACK, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(WHITE, curses.COLOR_WHITE, curses.COLOR_BLACK)
    stdscr.nodelay(1)
    my, mx = stdscr.getmaxyx()
    win = WinWrap(curses.newpad(2000, 2000), 1, 1)
    key = 0
    # interval = args.interval
    while key not in (ord('q'), ord('Q')):
        win.addln("Running Checks...", curses.color_pair(BLACK))
        win.clrtoeol()
        win.refresh(0, 0, 0, 0, my-1, mx-1)
        common.reset_checks()
        load_checks(config, plugins=args.use_plugins, tags=args.tags,
                    not_tags=args.not_tags)
        s = StringIO.StringIO()
        gen_report(outfile=s, quiet=args.quiet, ojson=args.json)

        # Draw Report
        win.clear()
        win.refresh(0, 0, 0, 0, my-1, mx-1)
        win.addln("Updated: " + str(datetime.datetime.now()))
        win.addln("Plugins: {}".format(", ".join(args.use_plugins)))
        win.addln("Tags: {}".format(", ".join(args.tags)))
        win.addln("Not Tags: {}".format(", ".join(args.not_tags)))
        s.seek(0)
        data = common.strip_invisible(s.read())
        data = data.splitlines()
        for line in data:
            parts = line.split("|")
            if line[0] == "|":
                win.addsameln("|")
                for part in parts:
                    cp = 0
                    if not part:
                        continue
                    elif "FAIL" in part:
                        cp = curses.color_pair(RED)
                    elif "Success" in part:
                        cp = curses.color_pair(GREEN)
                    elif "WARN" in part:
                        cp = curses.color_pair(YELLOW)
                    elif "ISSUE" in part:
                        length = 15
                        prefix = part[:length]
                        part = part[length:]
                        win.addsameln(prefix, curses.color_pair(MAGENTA))
                    elif "FIX" in part:
                        length = 13
                        prefix = part[:length]
                        part = part[length:]
                        win.addsameln(prefix, curses.color_pair(CYAN))
                    win.addsameln(part, cp)
                    win.addsameln("|")
                win.endln()
            else:
                win.addln(line)
        # Check for character
        timeout = float(args.interval)
        win.addln("")
        win.addln("Press 'q' or 'Q' to exit")
        win.addln("Press 'r' or 'R' to reload")
        win.refresh(0, 0, 0, 0, my-1, mx-1)
        while timeout > 0:
            key = win.getch()
            if key in (ord('q'), ord('Q')):
                curses.curs_set(VISIBLE)
                curses.endwin()
                return
            elif key in (ord('r'), ord('R')):
                break
            time.sleep(0.2)
            timeout -= 0.2
