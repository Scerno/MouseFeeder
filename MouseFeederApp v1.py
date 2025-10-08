import threading
import time
import tkinter as tk
from tkinter import ttk
import pyvjoy
import pyautogui
from screeninfo import get_monitors
from pynput import mouse as pynput_mouse

# --- Worker class -------------------------------------------------------------

class MouseFeeder:
    def __init__(self):
        self.running = False
        self.settings = {
            "deadzone": 0.3,
            "sensitivity": 0.003,
            "invert_y": True,
            "update_hz": 120
        }
        self.j = pyvjoy.VJoyDevice(1)
        self.z_val = 0.0
        self.listener = None

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self.run, daemon=True).start()
        self.listener = pynput_mouse.Listener(on_scroll=self.on_scroll)
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()
            self.listener = None

    def on_scroll(self, x, y, dx, dy):
        self.z_val = max(-1.0, min(1.0, self.z_val + dy * 0.05))

    def run(self):
        mx, my = pyautogui.position()
        mon = next((m for m in get_monitors() if m.x <= mx < m.x + m.width and m.y <= my < m.y + m.height), get_monitors()[0])
        cx, cy = mon.x + mon.width/2, mon.y + mon.height/2

        center, rng = 16384, 16384
        while self.running:
            x, y = pyautogui.position()
            rel_x = (x - cx) / (mon.width / 2)
            rel_y = (y - cy) / (mon.height / 2)
            if self.settings["invert_y"]:
                rel_y = -rel_y

            rel_x = max(-1.0, min(1.0, rel_x))
            rel_y = max(-1.0, min(1.0, rel_y))

            dz = self.settings["deadzone"]
            def apply_deadzone(v):
                if abs(v) < dz:
                    return 0
                return (v - dz if v > 0 else v + dz) / (1 - dz)
            rel_x = apply_deadzone(rel_x)
            rel_y = apply_deadzone(rel_y)

            vx = int(rel_x * rng + center)
            vy = int(rel_y * rng + center)
            vz = int(self.z_val * rng + center)
            self.j.set_axis(pyvjoy.HID_USAGE_X, vx)
            self.j.set_axis(pyvjoy.HID_USAGE_Y, vy)
            self.j.set_axis(pyvjoy.HID_USAGE_Z, vz)

            time.sleep(1 / self.settings["update_hz"])

# --- GUI ---------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mouse to vJoy Feeder")
        self.geometry("300x280")
        self.feeder = MouseFeeder()
        self.create_ui()

    def create_ui(self):
        pad = {'padx': 10, 'pady': 5}

        ttk.Label(self, text="Deadzone (0–1):").pack(**pad)
        self.deadzone = tk.DoubleVar(value=0.3)
        ttk.Entry(self, textvariable=self.deadzone).pack(**pad)

        ttk.Label(self, text="Sensitivity:").pack(**pad)
        self.sensitivity = tk.DoubleVar(value=0.003)
        ttk.Entry(self, textvariable=self.sensitivity).pack(**pad)

        ttk.Label(self, text="Update Hz:").pack(**pad)
        self.update_hz = tk.IntVar(value=60)
        ttk.Entry(self, textvariable=self.update_hz).pack(**pad)

        self.invert_y = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Invert Y", variable=self.invert_y).pack(**pad)

        self.btn = ttk.Button(self, text="Start", command=self.toggle)
        self.btn.pack(pady=15)

        ttk.Label(self, text="Mouse position controls X/Y axes.\n"
                             "Scroll wheel controls Z axis.\n"
                             "vJoy must be installed first.", justify="center").pack(pady=10)

    def toggle(self):
        if self.feeder.running:
            self.feeder.stop()
            self.btn.config(text="Start")
        else:
            self.feeder.settings.update({
                "deadzone": self.deadzone.get(),
                "sensitivity": self.sensitivity.get(),
                "invert_y": self.invert_y.get(),
                "update_hz": self.update_hz.get()
            })
            self.feeder.start()
            self.btn.config(text="Stop")

if __name__ == "__main__":
    App().mainloop()
