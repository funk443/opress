# opress: a simple input tracker based on libinput.
# Copyright (C) 2024  CToID <funk443@yahoo.com.tw>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
import subprocess
import sys

# Libinput related stuffs.

class ProcInput():
    def __init__(
            self,
            device = None,
            show_key_codes = True):
        args = ["sudo", "libinput", "debug-events"]
        if show_key_codes:
            args.append("--show-keycodes")

        if device is not None:
            args.extend(["--device", device])

        self.proc = subprocess.Popen(
            args = args,
            stdout = subprocess.PIPE)

    def line_iter(self):
        def read_fn():
            line = self.proc.stdout.readline()
            return line.decode("UTF-8").strip()
        return iter(read_fn, "")

    def exit(self):
        self.proc.terminate()
        return self.proc.returncode

class KeyChange():
    def __init__(self, mode, key_name = None, key_code = None):
        self.mode = mode
        self.name = key_name
        self.code = key_code

REGEXP_PRESSED = re.compile(r"([a-zA-Z0-9_*]+) \(([-0-9]+)\) pressed")
REGEXP_RELEASED = re.compile(r"([a-zA-Z0-9_*]+) \(([-0-9]+)\) released")

def parse_line(line):
    match = re.search(REGEXP_PRESSED, line)
    if match is not None:
        return KeyChange(
            mode = "pressed",
            key_name = match.group(1),
            key_code = int(match.group(2)))

    match = re.search(REGEXP_RELEASED, line)
    if match is not None:
        return KeyChange(
            mode = "released",
            key_name = match.group(1),
            key_code = int(match.group(2)))

    return KeyChange(mode = "unknown")

# Terminal related stuffs.

CSI = "\033["
ERASE_ALL = CSI + "2J"
ERASE_ENTIRE_LINE = CSI + "2K"
RESET_ALL = CSI + "0m"
BG_RED = CSI + "41m"

def echo_off():
    subprocess.run(["stty", "-echo"], check = True)

def echo_on():
    subprocess.run(["stty", "echo"], check = True)

def clear_screen():
    print(ERASE_ALL, end = "")

def set_bg_red():
    print(BG_RED, end = "")

def reset_all():
    print(RESET_ALL, end = "")

def move_cursor(n, m):
    print(f"{CSI}{n};{m}H", end = "")

def erase_line():
    print(ERASE_ENTIRE_LINE, end= "")

# Logic related stuffs.

def generate_watch_keys(line_iter):
    clear_screen()
    move_cursor(1, 1)
    print("Press ESC to finish the setup.")

    watch_keys = {}

    for line in line_iter:
        move_cursor(2, 1)
        erase_line()
        print(f"Keys to check: {[k for k in watch_keys.keys()]}")
        key_change = parse_line(line)

        if (key_change.name == "KEY_ESC"):
            return watch_keys

        if (key_change.mode == "pressed" and
            key_change.name not in watch_keys):
            watch_keys[key_change.name] = False
            continue

        if (key_change.mode == "pressed" and
            key_change.name in watch_keys):
            del watch_keys[key_change.name]
            continue

def refresh_watch_keys(key_change, watch_keys):
    if key_change.name not in watch_keys:
        return

    if key_change.mode == "pressed":
        watch_keys[key_change.name] = True
        return

    if key_change.mode == "released":
        watch_keys[key_change.name] = False
        return

# Entry point.

if __name__ == "__main__":
    echo_off()

    proc = None
    if len(sys.argv) >= 2:
        proc = ProcInput(device = sys.argv[1])
    else:
        proc = ProcInput()

    watch_keys = generate_watch_keys(proc.line_iter())
    clear_screen()
    move_cursor(1, 1)
    print("Press Ctrl-C to exit the program.")

    try:
        for line in proc.line_iter():
            move_cursor(2, 1)

            refresh_watch_keys(
                key_change = parse_line(line),
                watch_keys = watch_keys)

            for k, v in watch_keys.items():
                if v:
                    set_bg_red()
                print(k)
                reset_all()

    except KeyboardInterrupt:
        echo_on()
        exit(proc.exit())
