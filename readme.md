# MouseFeeder

**MouseFeeder** is a lightweight Python app that converts mouse movement and scroll input into a virtual joystick signal using vJoy.  
Perfect for simulator setups or games that only support joystick input.

## Features
- Real-time mouse → joystick mapping (X/Y/Z)
- Adjustable deadzone, sensitivity, and update rate
- Simple Tkinter GUI with saved settings
- Compatible with vJoy 2.1.8+

## Requirements
- Windows 10/11
- [vJoy](http://vjoystick.sourceforge.net/)
- Python 3.10+
- Modules: `pyvjoy`, `pyautogui`, `pynput`, `screeninfo`, `tkinter`

## Usage
```bash
python MouseFeederApp.py
