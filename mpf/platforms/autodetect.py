import serial.tools.list_ports
import re

from mpf.exceptions.runtime_error import MpfRuntimeError

def autodetect_fast_ports(is_retro=False):
    if is_retro:
        return _find_fast_retro()
    return _find_fast_quad()

def autodetect_smartmatrix_dmd_port():
    return _find_fast_quad()[0]

def _find_fast_retro():
    devices = [port.device for port in serial.tools.list_ports.comports()]
    for d in devices:
        if re.search(r'\.usbmodem\d+$', d) or re.search(r'ACM\d$', d):
            return [d]
    raise MpfRuntimeError("Unable to auto-detect FAST Retro from available devices: {}".format(
                                      ", ".join(devices)), 1, "autodetect.find_fast_retro")

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
        raise MpfRuntimeError("Unable to auto-detect FAST hardware from available devices: {}".format(
                                      ", ".join(devices)), 1, "autodetect.find_fast_quad")
    return ports
