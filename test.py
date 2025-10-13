from pynput import keyboard

keys_pressed = set()

def on_press(key):
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

    keys_pressed.add(name)
    print(f"Pressed: {name} | Current keys: {sorted(list(keys_pressed))}")

def on_release(key):
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

    if name in keys_pressed:
        keys_pressed.remove(name)
    print(f"Released: {name} | Current keys: {sorted(list(keys_pressed))}")

    if key == keyboard.Key.esc:
        print("Exiting...")
        return False

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print("Press any key (ESC to quit)...")
    listener.join()
