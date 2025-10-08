import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path
import threading
import time
import pyvjoy
import pyautogui
from screeninfo import get_monitors
from pynput import mouse as pynput_mouse

# ---------------------------------------------------------------------------
# MouseFeeder class
# ---------------------------------------------------------------------------

class MouseFeeder:
    def __init__(self):
        self.running = False
        self.settings = {
            "deadzone": 0.2,
            "sensitivity": 1.0,
            "invert_y": True,
            "update_hz": 120
        }
        self.j = pyvjoy.VJoyDevice(1)
        self.z_val = 0.0
        self.listener = None

    def start(self):
        if self.running:
            return
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
        mon = next((m for m in get_monitors()
                    if m.x <= mx < m.x + m.width and m.y <= my < m.y + m.height),
                   get_monitors()[0])
        cx, cy = mon.x + mon.width / 2, mon.y + mon.height / 2
        centre, rng = 16384, 16384

        while self.running:
            x, y = pyautogui.position()
            rel_x = (x - cx) / (mon.width / 2)
            rel_y = (y - cy) / (mon.height / 2)
            
            # Apply sensitivity scaling
            rel_x *= self.settings["sensitivity"]
            rel_y *= self.settings["sensitivity"]

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

            vx = int(rel_x * rng + centre)
            vy = int(rel_y * rng + centre)
            vz = int(self.z_val * rng + centre)
            self.j.set_axis(pyvjoy.HID_USAGE_X, vx)
            self.j.set_axis(pyvjoy.HID_USAGE_Y, vy)
            self.j.set_axis(pyvjoy.HID_USAGE_Z, vz)

            time.sleep(1 / self.settings["update_hz"])


# ---------------------------------------------------------------------------
# App class (GUI)
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mouse to vJoy Feeder")
        self.geometry("650x950")
        self.settings_path = Path(__file__).with_name("settings.json")

        self.feeder = MouseFeeder()
        self._load_settings()
        self._create_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        pad = {'padx': 10, 'pady': 5}
        self.inputs = []  # keep track of editable widgets

        def validate_numeric(new_value):
            if new_value == "" or new_value.replace(".", "", 1).isdigit():
                return True
            return False

        vcmd = (self.register(validate_numeric), "%P")

        ttk.Label(self, text="Deadzone (0–1):").pack(**pad)
        self.deadzone = tk.DoubleVar(value=self.last_settings.get("deadzone", 0.3))
        e1 = ttk.Entry(self, textvariable=self.deadzone, validate="key", validatecommand=vcmd)
        e1.pack(**pad)
        self.inputs.append(e1)

        ttk.Label(self, text="Sensitivity:").pack(**pad)
        self.sensitivity = tk.DoubleVar(value=self.last_settings.get("sensitivity", 1.0))
        e2 = ttk.Entry(self, textvariable=self.sensitivity, validate="key", validatecommand=vcmd)
        e2.pack(**pad)
        self.inputs.append(e2)

        ttk.Label(self, text="Update Hz:").pack(**pad)
        self.update_hz = tk.IntVar(value=self.last_settings.get("update_hz", 60))
        e3 = ttk.Entry(self, textvariable=self.update_hz, validate="key", validatecommand=vcmd)
        e3.pack(**pad)
        self.inputs.append(e3)

        self.invert_y = tk.BooleanVar(value=self.last_settings.get("invert_y", True))
        cb = ttk.Checkbutton(self, text="Invert Y", variable=self.invert_y)
        cb.pack(**pad)
        self.inputs.append(cb)

        self.btn = ttk.Button(self, text="Start", command=self._toggle)
        self.btn.pack(pady=15)
        
        ttk.Label(self, text="Purpose", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        
        ttk.Label(self, text="Mouse position controls X/Y axes in a linear scale.\n"
                             "Scroll wheel controls Z axis.",
                  justify="center", wraplength=630).pack(padx=10, pady=10)
                             
        ttk.Label(self, text="Instructions", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        
        ttk.Label(self, text="First make sure vJoy is installed.\nThen click Start to activate.\nTest settings before using in game (recommend using vJoy Monitor application). ",
                  justify="center", wraplength=630).pack(padx=10, pady=10)
                  
        ttk.Label(self, text="Multiple Monitors", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        ttk.Label(self, text="If you have multiple monitors, note that the monitor that the mouse is in when you click Start will be the one used for calculating joystick position.",
                  justify="center", wraplength=630).pack(padx=10, pady=10)
        
        ttk.Label(self, text="Notes", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        
        ttk.Label(self, text="- Deadzone: Default = 0.2.  This is a deadzone in the centre of the screen.  0.2 = 20% of mouse travel distance.",
                  justify="left", wraplength=630).pack(padx=10, pady=3)
        ttk.Label(self, text="- Sensitivity: Default = 1.  At 1, joystick reaches full movement at edges of screen.  Doubling sensitivity to 2 makes the joystick reach full movement in half the distance.",
                  justify="left", wraplength=630).pack(padx=10, pady=3)
        ttk.Label(self, text="- Update Hz: Default = 60.  This is how often the joystick updates in Hertz.  Match your mouse speed for smooth movement.",
                  justify="left", wraplength=630).pack(padx=10, pady=3)


    def _toggle(self):
        if self.feeder.running:
            # Stop feeder
            self.feeder.stop()
            self.btn.config(text="Start")

            # Re-enable input widgets
            for w in self.inputs:
                try:
                    w.configure(state="normal")
                except tk.TclError:
                    # ttk.Checkbutton uses alternate names
                    w.state(["!disabled"])
        else:
            # Update settings
            self.feeder.settings.update({
                "deadzone": self.deadzone.get(),
                "sensitivity": self.sensitivity.get(),
                "invert_y": self.invert_y.get(),
                "update_hz": self.update_hz.get()
            })
            self.feeder.start()
            self.btn.config(text="Stop")

            # Disable input widgets
            for w in self.inputs:
                try:
                    w.configure(state="disabled")
                except tk.TclError:
                    w.state(["disabled"])


    def _on_close(self):
        self._save_settings()
        self.feeder.stop()
        self.destroy()

    def _save_settings(self):
        data = {
            "deadzone": self.deadzone.get(),
            "sensitivity": self.sensitivity.get(),
            "invert_y": self.invert_y.get(),
            "update_hz": self.update_hz.get()
        }
        with open(self.settings_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_settings(self):
        if self.settings_path.exists():
            with open(self.settings_path) as f:
                self.last_settings = json.load(f)
        else:
            self.last_settings = {}


if __name__ == "__main__":
    App().mainloop()
