# Copyright (c) 2013 Michael Bitzi
# Licensed under the MIT license http://opensource.org/licenses/MIT

from unittest.mock import patch

from pwm.config import config
from pwm.ffi.xcb import xcb
import pwm.root
import pwm.bar
import pwm.workspaces

connected = False
created_windows = []


def setup():
    config.load(default=True)

    # To increase test speed we only want to connect once
    global connected
    if not connected:
        xcb.connect()
        pwm.root.setup()
        connected = True

    pwm.workspaces.setup()
    pwm.bar.setup()


def tear_down():
    destroy_created_windows()
    pwm.bar.destroy()
    pwm.workspaces.destroy()
    pwm.windows.managed = {}


def create_window(manage=True, floating=False, fullscreen=False):
    """Create a new window and manage it."""

    wid = pwm.windows.create(0, 0, 100, 100)

    if manage:
        with patch.object(pwm.windows, "should_float", return_value=floating):
            pwm.windows.manage(wid)
    else:
        pwm.windows.managed[wid] = pwm.windows.Info()
        pwm.windows.managed[wid].floating = floating

    pwm.windows.managed[wid].fullscreen = fullscreen

    global created_windows
    created_windows.append((wid, manage))

    return wid


def destroy_created_windows():
    """Destroy all created windows.

    This function will be called during tear_down().
    """
    global created_windows
    for wid, managed in created_windows:
        if managed:
            pwm.windows.unmanage(wid)
        pwm.windows.destroy(wid)
    created_windows = []
