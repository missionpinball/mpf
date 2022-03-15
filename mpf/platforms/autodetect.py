"""Methods for auto-detecting platform hardware from available serial devices."""

import re
import serial.tools.list_ports

from mpf.exceptions.runtime_error import MpfRuntimeError


def autodetect_fast_ports(is_retro=False):
    """Search the serial devices for a FAST platform."""
    if is_retro:
        return _find_fast_retro()
    return _find_fast_quad()


def autodetect_smartmatrix_dmd_port():
    """Search the serial devices for a FAST SmartMatrix DMD."""
    return _find_fast_quad()[0]


def _find_fast_retro():
    devices = [port.device for port in _get_sorted_ports()]
    for d in devices:
        if re.search(r'\.usbmodem\d+$', d) or re.search(r'ACM\d$', d) or re.search(r'COM\d$', d):
            return [d]
    raise MpfRuntimeError(f"Unable to auto-detect FAST Retro from available devices: {', '.join(devices)}",
                          1, "autodetect.find_fast_retro")


def _find_fast_quad():
    ports = None
    devices = [port.device for port in _get_sorted_ports()]
    # Look for four devices with sequential tails of 0-3 or A-D
    seqs = (("0", "1", "2", "3"), ("A", "B", "C", "D"))
    for d in devices:
        for seq in seqs:
            if d[-1] == seq[0]:
                root = d[:-1]
                if f"{root}{seq[1]}" in devices and f"{root}{seq[2]}" in devices and f"{root}{seq[3]}" in devices:
                    ports = [f"{root}{i}" for i in seq]
                    break
        # If ports were found, skip the rest of the devices
        if ports:
            break
    if not ports:
        raise MpfRuntimeError(f"Unable to auto-detect FAST hardware from available devices: {', '.join(devices)}",
                              1, "autodetect.find_fast_quad")
    return ports


def _get_sorted_ports():
    ports = serial.tools.list_ports.comports()
    ports.sort()
    return ports
