import pyvjoy, time

j = pyvjoy.VJoyDevice(1)

for pov in [0, 1, 2, 3]:
    try:
        j.set_cont_pov(0, pov)
        print(f"POV {pov} OK")
    except pyvjoy.exceptions.vJoyInvalidPovIDException:
        print(f"POV {pov} invalid")
