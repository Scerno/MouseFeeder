import pyvjoy
import pyautogui
from screeninfo import get_monitors
import time

# --- Settings ---
DEADZONE = 0.2          # Fraction of screen (0.0–1.0) ignored around centre
UPDATE_HZ = 60          # Refresh rate (higher = smoother)
INVERT_Y = True         # Flip Y axis if needed

# --- Setup ---
j = pyvjoy.VJoyDevice(1)

# Detect which screen the mouse is currently on
def get_current_monitor(mouse_x, mouse_y):
    for m in get_monitors():
        if m.x <= mouse_x < m.x + m.width and m.y <= mouse_y < m.y + m.height:
            return m
    return get_monitors()[0]  # fallback to first if not found

# Get mouse position and monitor info
mx, my = pyautogui.position()
monitor = get_current_monitor(mx, my)
print(f"Detected monitor: {monitor.name or 'Primary'} ({monitor.width}x{monitor.height})")

# Precompute screen bounds
left = monitor.x
top = monitor.y
width = monitor.width
height = monitor.height
center_x = left + width / 2
center_y = top + height / 2

def apply_deadzone(value, deadzone):
    if abs(value) < deadzone:
        return 0.0
    # Smoothly rescale so full output occurs near screen edges
    if value > 0:
        return (value - deadzone) / (1 - deadzone)
    else:
        return (value + deadzone) / (1 - deadzone)

# --- Main loop ---
print("Running...  (Ctrl+C to quit)")
CENTER = 16384
RANGE = 16384

while True:
    x, y = pyautogui.position()

    # Normalise position to -1..1 range within this screen
    rel_x = ((x - center_x) / (width / 2))
    rel_y = ((y - center_y) / (height / 2))
    if INVERT_Y:
        rel_y = -rel_y

    # Clamp and apply deadzone
    rel_x = max(-1.0, min(1.0, rel_x))
    rel_y = max(-1.0, min(1.0, rel_y))
    rel_x = apply_deadzone(rel_x, DEADZONE)
    rel_y = apply_deadzone(rel_y, DEADZONE)

    # Convert to vJoy axis range (0–32767)
    vx = int(rel_x * RANGE + CENTER)
    vy = int(rel_y * RANGE + CENTER)

    j.set_axis(pyvjoy.HID_USAGE_X, vx)
    j.set_axis(pyvjoy.HID_USAGE_Y, vy)

    time.sleep(1 / UPDATE_HZ)
