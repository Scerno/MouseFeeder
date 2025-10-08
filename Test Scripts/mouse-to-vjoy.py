import pyvjoy
import pyautogui
from screeninfo import get_monitors
import mouse
import time

# --- Settings ---
DEADZONE = 0.3
UPDATE_HZ = 60
INVERT_Y = True
SCROLL_SENSITIVITY = 0.05   # adjust how far each scroll step moves Z
Z_DECAY = 0.98               # how fast Z recentres (1.0 = hold value forever)

# --- Setup ---
j = pyvjoy.VJoyDevice(1)
CENTER = 16384
RANGE  = 16384

# --- Detect monitor (same as before) ---
def get_current_monitor(x, y):
    for m in get_monitors():
        if m.x <= x < m.x + m.width and m.y <= y < m.y + m.height:
            return m
    return get_monitors()[0]

mx, my = pyautogui.position()
mon = get_current_monitor(mx, my)
left, top, width, height = mon.x, mon.y, mon.width, mon.height
cx, cy = left + width / 2, top + height / 2
print(f"Detected monitor: {mon.name or 'Primary'}  ({width}x{height})")

# --- Helpers ---
def clamp(v, lo=-1, hi=1): return max(lo, min(hi, v))
def apply_deadzone(v, dz):
    if abs(v) < dz: return 0.0
    return (v - dz if v > 0 else v + dz) / (1 - dz)

# --- Scroll-wheel handler ---
from pynput import mouse as pynput_mouse
import threading

z_val = 0.0

def on_scroll(x, y, dx, dy):
    global z_val
    # dy = +1 (scroll up) or -1 (scroll down)
    z_val = clamp(z_val + dy * SCROLL_SENSITIVITY)

# start the listener in a background thread
listener = pynput_mouse.Listener(on_scroll=on_scroll)
listener.daemon = True
listener.start()

# --- Main loop ---
while True:
    x, y = pyautogui.position()
    rel_x = clamp((x - cx) / (width / 2))
    rel_y = clamp((y - cy) / (height / 2))
    if INVERT_Y: rel_y = -rel_y

    rel_x = apply_deadzone(rel_x, DEADZONE)
    rel_y = apply_deadzone(rel_y, DEADZONE)

    vx = int(rel_x * RANGE + CENTER)
    vy = int(rel_y * RANGE + CENTER)
    vz = int(z_val  * RANGE + CENTER)

    j.set_axis(pyvjoy.HID_USAGE_X, vx)
    j.set_axis(pyvjoy.HID_USAGE_Y, vy)
    j.set_axis(pyvjoy.HID_USAGE_Z, vz)

    # optional slow return to centre
    # z_val *= Z_DECAY
    time.sleep(1 / UPDATE_HZ)
