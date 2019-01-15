from __future__ import (print_function, unicode_literals, division,
                        absolute_import)


import curses
import datetime
import time

from io import StringIO

from checkers import run_checks
from common import gen_report, reset_checks, strip_invisible

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

        self.win.nodelay(1)

    def addstr(self, y, x, s, color=0):
        self.x = x
        self.y = y
        self.win.addstr(self.y, self.x, s, curses.color_pair(color))

    def addsameln(self, s, color=0):
        self.win.addstr(self.y, self.x, s, curses.color_pair(color))
        self.x += len(s)

    def endln(self):
        self.x = self.xbase
        self.y += 1

    def addln(self, s, color=0):
        self.win.addstr(self.y, self.x, s, curses.color_pair(color))
        self.y += 1
        self.x = self.xbase

    def upy(self, y=1):
        self.x = self.xbase
        self.y -= y

    def refresh(self, *args):
        self.win.refresh(*args)

    def clear(self):
        self.win.clear()
        self.x = self.xbase
        self.y = self.ybase

    def clrtoeol(self):
        self.win.clrtoeol()

    def getch(self):
        return self.win.getch()

    def subpad(self, *args):
        return self.win.subpad(*args)

    def redrawln(self, *args):
        self.win.redrawln(*args)


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
    my, mx = stdscr.getmaxyx()
    win = WinWrap(curses.newpad(2000, 2000), 1, 1)
    key = 0
    # interval = args.interval
    while key not in (ord('q'), ord('Q')):
        win.addln("Running Checks...", BLACK)
        win.clrtoeol()
        win.refresh(0, 0, 0, 0, my-1, mx-1)
        reset_checks()
        run_checks(config, plugins=args.use_plugins, tags=args.tags,
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
        data = strip_invisible(s.read())
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
                        cp = RED
                    elif "Success" in part:
                        cp = GREEN
                    elif "WARN" in part:
                        cp = YELLOW
                    elif "ISSUE" in part:
                        length = 15
                        prefix = part[:length]
                        part = part[length:]
                        win.addsameln(prefix, MAGENTA)
                    elif "FIX" in part:
                        length = 13
                        prefix = part[:length]
                        part = part[length:]
                        win.addsameln(prefix, CYAN)
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
        win.addln("Press 'p' or 'P' to pause")
        win.refresh(0, 0, 0, 0, my-1, mx-1)
        while timeout > 0:
            key = win.getch()
            win.addln("Checks will be run in {} seconds".format(timeout))
            win.clrtoeol()
            win.upy()
            win.redrawln(win.y, 1)
            win.refresh(0, 0, 0, 0, my-1, mx-1)
            if key < 0:
                time.sleep(0.2)
                timeout -= 0.2
                continue
            if key in (ord('q'), ord('Q')):
                curses.curs_set(VISIBLE)
                curses.endwin()
                return
            elif key in (ord('r'), ord('R')):
                break
            elif key in (ord('p'), ord('P')):
                win.addln("Press any key to unpause", BLACK)
                win.clrtoeol()
                win.upy()
                win.refresh(0, 0, 0, 0, my-1, mx-1)
                subkey = -1
                while subkey == -1:
                    subkey = win.getch()
                    time.sleep(0.1)
                win.addln("")
                win.clrtoeol()
                win.upy()
                win.refresh(0, 0, 0, 0, my-1, mx-1)
