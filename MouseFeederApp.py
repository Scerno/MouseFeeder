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
import math
import ctypes


# Force pyvjoy to use the system vJoy DLL instead of its embedded one
try:
    pyvjoy._sdk._vj = ctypes.WinDLL(r"C:\Program Files\vJoy\x64\vJoyInterface.dll")
    print("✅ Loaded system vJoyInterface.dll successfully.")
except Exception as e:
    print("⚠️ Could not load system vJoy DLL:", e)
    

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
# POVFeeder class
# ---------------------------------------------------------------------------
from pynput import keyboard
import ctypes, math, threading, time

class POVFeeder:
    def __init__(self):
        self.running = False
        self.keys_pressed = set()
        self.listener = None
        self.update_hz = 60

        # Load vJoy DLL and required functions
        dll_path = r"C:\Program Files\vJoy\x64\vJoyInterface.dll"
        self.vj = ctypes.WinDLL(dll_path)

        # Define function prototypes
        self.AcquireVJD   = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)(("AcquireVJD", self.vj))
        self.RelinquishVJD = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)(("RelinquishVJD", self.vj))
        self.ResetVJD     = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)(("ResetVJD", self.vj))
        self.SetContPov   = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint32, ctypes.c_uint, ctypes.c_ubyte)(("SetContPov", self.vj))

        self.device_id = 1
        self.pov_h = 1  # POV1 = horizontal
        self.pov_v = 2  # POV2 = vertical

    # -------------------------
    # Lifecycle control
    # -------------------------
    def start(self):
        if self.running:
            return
        if not self.AcquireVJD(self.device_id):
            print("❌ Could not acquire vJoy device.")
            return

        print("✅ Acquired vJoy device", self.device_id)
        self.running = True
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.RelinquishVJD(self.device_id)
        print("✅ Released vJoy device")

    # -------------------------
    # Keyboard handling
    # -------------------------
    def on_press(self, key):
        try:
            if key.char is not None:
                name = key.char
            else:
                # Handle numpad by VK code
                if hasattr(key, "vk") and 96 <= key.vk <= 105:
                    name = f"numpad{key.vk - 96}"  # numpad0–9
                else:
                    name = str(key)
        except AttributeError:
            name = str(key)

        self.keys_pressed.add(name)
        # Debug output
        # print(f"Pressed: {name}")

    def on_release(self, key):
        try:
            if key.char is not None:
                name = key.char
            else:
                if hasattr(key, "vk") and 96 <= key.vk <= 105:
                    name = f"numpad{key.vk - 96}"
                else:
                    name = str(key)
        except AttributeError:
            name = str(key)

        if name in self.keys_pressed:
            self.keys_pressed.remove(name)
            print(f"Released: {name}")


    # -------------------------
    # POV calculation logic
    # -------------------------
    def calculate_angles(self):
        kp = self.keys_pressed
        horiz = None
        vert = None

        # --- Horizontal POV1 (Num7–9–4–6–1–3–8–2)
        horiz_map = {
            "numpad8": 0,    # forward
            "numpad9": 45,   # 45° right
            "numpad6": 90,   # right
            "numpad3": 135,  # 135° right (back-right)
            "numpad2": 180,  # backward
            "numpad1": 225,  # 135° left (back-left)
            "numpad4": 270,  # left
            "numpad7": 315,  # 45° left (front-left)
        }

        pressed_horiz_keys = [horiz_map[k] for k in horiz_map if k in kp]
        if pressed_horiz_keys:
            x = sum([math.cos(math.radians(a)) for a in pressed_horiz_keys]) / len(pressed_horiz_keys)
            y = sum([math.sin(math.radians(a)) for a in pressed_horiz_keys]) / len(pressed_horiz_keys)
            horiz = (math.degrees(math.atan2(y, x)) + 360) % 360

        # --- Vertical POV2 (Num5, Num0)
        up = "numpad5" in kp
        down = "numpad0" in kp
        horiz_active = bool(pressed_horiz_keys)

        if up and not down:
            vert = 45.0 if horiz_active else 90.0
        elif down and not up:
            vert = -45.0 if horiz_active else -90.0
        elif horiz_active:
            vert = 0.0

        # Return None if nothing is pressed at all
        if horiz is None and vert is None:
            return None, None
        return horiz or 0.0, vert or 0.0


    # -------------------------
    # Main loop
    # -------------------------
    def run(self):
        print("🔍 POVFeeder active. Watching for NumPad keys...")
        last_keys = set()
        last_angles = (None, None)

        while self.running:
            h, v = self.calculate_angles()

            if self.keys_pressed != last_keys:
                print(f"Keys pressed: {sorted(list(self.keys_pressed))}")
                last_keys = set(self.keys_pressed)

            if h is not None and v is not None:
                # Convert to vJoy angles
                h_val = ctypes.c_uint32(int(h * 100))
                pov2_angle = (90 - v) % 360
                # v_val = ctypes.c_uint32(int(pov2_angle * 100))
                v_val = ctypes.c_uint32(int(((v + 90 - 90) % 360) * 100))


                if (round(h, 1), round(v, 1)) != last_angles:
                    print(f" → Calculated angles: horiz={h:.1f}°, vert={v:.1f}°")
                    last_angles = (round(h, 1), round(v, 1))

                self.SetContPov(h_val, self.device_id, self.pov_h)
                self.SetContPov(v_val, self.device_id, self.pov_v)
            else:
                # No keys pressed → neutral
                neutral = ctypes.c_uint32(0xFFFFFFFF)
                self.SetContPov(neutral, self.device_id, self.pov_h)
                self.SetContPov(neutral, self.device_id, self.pov_v)
                last_angles = (None, None)

            time.sleep(1 / self.update_hz)







# ---------------------------------------------------------------------------
# App class (GUI)
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        APP_VERSION = "1.1.0"
        self.title(f"MouseFeeder v{APP_VERSION}")
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
        
        self.enable_pov = tk.BooleanVar(value=False)
        cb2 = ttk.Checkbutton(self, text="Enable NumPad POV Camera", variable=self.enable_pov)
        cb2.pack(**pad)
        self.inputs.append(cb2)
        
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
            
            # POV toggle
            if hasattr(self, "pov_feeder"):
                self.pov_feeder.stop()
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
            
            # POV toggle
            if self.enable_pov.get():
                self.pov_feeder = POVFeeder()
                self.pov_feeder.start()
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
