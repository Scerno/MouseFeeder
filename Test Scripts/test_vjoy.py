import pyvjoy
import time

# Connect to vJoy Device ID 1
j = pyvjoy.VJoyDevice(1)

# Range: 0–32767, midpoint is 16384
MID = 16384
MAX = 32767
MIN = 0

# Sweep X axis left and right
while True:
    for val in range(MIN, MAX, 1000):
        j.set_axis(pyvjoy.HID_USAGE_X, val)
        time.sleep(0.01)
    for val in range(MAX, MIN, -1000):
        j.set_axis(pyvjoy.HID_USAGE_X, val)
        time.sleep(0.01)
