import serial.tools.list_ports
import re

def autodetect_fast_ports(machine_type="fast"):
    if machine_type == "fast":
        return _find_fast_quad()
    elif machine_type == "retro":
        return _find_fast_retro()

    raise KeyError("Unknown machine type '{}' for autodetecting FAST ports.".format(machine_type))

def autodetect_smartmatrix_dmd_port():
    return _find_fast_quad()[0]

def _find_fast_retro():
    devices = [port.device for port in serial.tools.list_ports.comports()]
    for d in devices:
        print("Looking at device {}".format(d))
        if re.search(r'\.usbmodem\d+$',d):
            print("!!MATCH")
            return [d]

def _find_fast_quad():
    ports = None
    devices = [port.device for port in serial.tools.list_ports.comports()]
    # Look for four devices with sequential tails of 0-3 or A-D
    seqs = (("0", "1", "2", "3"), ("A", "B", "C", "D"))
    for d in devices:
        for seq in seqs:
            if d[-1] == seq[0]:
                root = d[:-1]
                if "{}{}".format(root, seq[1]) in devices and \
                    "{}{}".format(root, seq[2]) in devices and \
                    "{}{}".format(root, seq[3]) in devices:
                    ports = ["{}{}".format(root, i) for i in seq]
                    break
        # If ports were found, skip the rest of the devices
        if ports:
            break
    if not ports:
        raise RuntimeError("Unable to auto-detect FAST hardware from available devices: {}".format(
                            ", ".join(devices)))
    return ports
