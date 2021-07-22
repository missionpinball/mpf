import serial.tools.list_ports
import re

from mpf.exceptions.runtime_error import MpfRuntimeError

def autodetect_fast_ports(machine_type="fast"):
    if machine_type == "retro":
        # Retro boards are always v2
        return _find_fast_v2()
    elif machine_type == "fast":
        # Look for a V1 machine first, since V1 ports are a superset of V2 ports
        return _find_fast_v1() or _find_fast_v2()
    else:
        raise KeyError("Unknown machine type '{}' for autodetecting FAST ports.".format(machine_type))

def autodetect_smartmatrix_dmd_port():
    return _find_fast_v1()[0]

def _find_fast_v2():
    devices = [port.device for port in serial.tools.list_ports.comports()]
    for d in devices:
        if re.search(r'\.usbmodem\d+$', d) or re.search(r'ACM\d$', d):
            return [d]
    raise MpfRuntimeError("Unable to auto-detect FAST hardware from available devices: {}".format(
                                      ", ".join(devices)), 1, "autodetect.find_fast_v2")

def _find_fast_v1():
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
    # Do not throw if no ports or found, we'll try looking for v2
    return ports
