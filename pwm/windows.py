# Copyright (c) 2013 Michael Bitzi
# Licensed under the MIT license http://opensource.org/licenses/MIT

from __future__ import division, absolute_import
from __future__ import print_function  # , unicode_literals

from contextlib import contextmanager
import struct

from pwm.ffi.xcb import xcb
from pwm.config import config
import pwm.color
import pwm.workspaces
import pwm.events

managed = {}
focused = None

MANAGED_EVENT_MASK = (xcb.EVENT_MASK_ENTER_WINDOW |
                      xcb.EVENT_MASK_FOCUS_CHANGE |
                      xcb.EVENT_MASK_PROPERTY_CHANGE)


#def create(x, y, width, height):
#    """Create a new window and return its id."""
#
#    wid = pwm.xcb.conn.generate_id()
#
#    mask, values = pwm.xcb.attribute_mask(
#        backpixel=pwm.xcb.screen.black_pixel,
#        eventmask=xproto.EventMask.Exposure)
#
#    pwm.xcb.core.CreateWindow(
#        pwm.xcb.screen.root_depth,
#        wid,
#        pwm.xcb.screen.root,
#        x, y,
#        width,
#        height,
#        0,  # border
#        xproto.WindowClass.InputOutput,
#        pwm.xcb.screen.root_visual,
#        mask, values)
#
#    return wid
#
#
#def destroy(wid):
#    """Destroy the window."""
#    pwm.xcb.core.DestroyWindow(wid)
#
#
def manage(wid):
    if wid in managed:
        return

    change_attributes(wid, [(xcb.CW_EVENT_MASK, MANAGED_EVENT_MASK)])

    managed[wid] = pwm.workspaces.current()
    pwm.workspaces.current().add_window(wid)

    handle_focus(wid)


def unmanage(wid):
    if wid not in managed:
        return

    ws = managed[wid]
    ws.remove_window(wid)
    del managed[wid]

    if focused == wid:
        handle_focus(pwm.workspaces.current().top_focus_priority())


def show(wid):
    """Map the given window."""
    xcb.core.map_window(wid)


def hide(wid):
    """Unmap the given window."""
    xcb.core.unmap_window(wid)


#def is_mapped(wid):
#    """Return True if the window is mapped, otherwise False."""
#    attr = pwm.xcb.core.GetWindowAttributes(wid).reply()
#    return attr.map_state == xproto.MapState.Viewable
#
#
def change_attributes(wid, masks):
    """Set attributes for the given window."""
    xcb.core.change_window_attributes(wid, *xcb.mask(masks))


#def get_name(wid):
#    """Get the window name."""
#
#    name = pwm.xcb.get_property_value(
#        pwm.xcb.get_property(wid, xproto.Atom.WM_NAME).reply())
#
#    return name or ""


def configure(wid, **kwargs):
    """Configure the window and set the given variables.

    Arguments can be: x, y, width, height
    """

    workspace = pwm.workspaces.current()
    values = [(xcb.CONFIG_WINDOW_BORDER_WIDTH, config.window.border)]

    if "x" in kwargs:
        values.append((xcb.CONFIG_WINDOW_X, int(workspace.x + kwargs["x"])))
    if "y" in kwargs:
        values.append((xcb.CONFIG_WINDOW_Y, int(workspace.y + kwargs["y"])))

    if "width" in kwargs:
        values.append((xcb.CONFIG_WINDOW_WIDTH,
                       int(kwargs["width"] - 2*config.window.border)))
    if "height" in kwargs:
        values.append((xcb.CONFIG_WINDOW_HEIGHT,
                       int(kwargs["height"] - 2*config.window.border)))

    xcb.core.configure_window(wid, *xcb.mask(values))


#def get_geometry(wid):
#    """Get geometry information for the given window.
#
#    Return a tuple(x, y, width, height).
#    """
#
#    geo = pwm.xcb.core.GetGeometry(wid).reply()
#    return (geo.x, geo.y, geo.width, geo.height)
#
#
#def get_wm_protocols(wid):
#    """Return the protocols supported by this window."""
#
#    return pwm.xcb.get_property_value(
#        pwm.xcb.get_property(wid, "WM_PROTOCOLS").reply())
#
#
#def kill(wid):
#    """Kill the window with wid."""
#
#    # Check if the window supports WM_DELETE_WINDOW, otherwise kill it
#    # the hard way.
#    if "WM_DELETE_WINDOW" in get_wm_protocols(wid):
#        vals = [
#            33,  # ClientMessageEvent
#            32,  # Format
#            0,
#            wid,
#            pwm.xcb.get_atom("WM_PROTOCOLS"),
#            pwm.xcb.get_atom("WM_DELETE_WINDOW"),
#            xproto.Time.CurrentTime,
#            0,
#            0,
#            0,
#        ]
#
#        event = struct.pack('BBHII5I', *vals)
#
#        pwm.xcb.core.SendEvent(False, wid, xproto.EventMask.NoEvent, event)
#
#    else:
#        pwm.xcb.core.KillClient(wid)
#
#
def handle_focus(wid):
    """Focus the window with the given wid.

    events.focus_changed will be fired with the new focused window as
    parameter. If no window was focused or the window was not found
    the event will be fired with None as parameter.
    """

    global focused

    win = wid if wid in managed else None

    if focused == win:
        return

    if focused:
        _handle_focus(focused, False)

    focused = win
    if focused:
        _handle_focus(focused, True)

    pwm.events.focus_changed(win)


def _handle_focus(wid, focused):
    """Set border color and input focus according to focus."""

    border = None
    if focused:
        border = pwm.color.get_pixel(config.window.focused)
    else:
        border = pwm.color.get_pixel(config.window.unfocused)

    change_attributes(wid, [(xcb.CW_BORDER_PIXEL, border)])

    if focused:
        xcb.core.set_input_focus(xcb.INPUT_FOCUS_POINTER_ROOT,
                                 wid,
                                 xcb.TIME_CURRENT_TIME)


@contextmanager
def no_enter_notify_event():
    """Prevent all managed windows from sending EnterNotifyEvent."""

    eventmask = MANAGED_EVENT_MASK
    eventmask &= ~xcb.EVENT_MASK_ENTER_WINDOW
    for wid in managed:
        change_attributes(wid, [(xcb.CW_EVENT_MASK, eventmask)])

    yield

    for wid in managed:
        change_attributes(wid, [(xcb.CW_EVENT_MASK, MANAGED_EVENT_MASK)])
