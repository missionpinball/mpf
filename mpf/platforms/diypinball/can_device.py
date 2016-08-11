import socket, struct, logging
from ctypes import c_uint

from .can_event import CANEvent


class CANDevice(object):
    FORMAT = struct.Struct("<IB3x8s")
    FD_FORMAT = struct.Struct("<IB3x64s")
    CAN_RAW_FD_FRAMES = 5

    def __init__(self, interface=None):
        self.sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        self.log = logging.getLogger('Platform.DIYPinball.CAN')
        if interface is not None:
            self.bind(interface)

    def enable_fd(self):
        self.sock.setsockopt(socket.SOL_CAN_RAW, self.CAN_RAW_FD_FRAMES, 1)

    def bind(self, interface):
        self.sock.bind((interface,))

    def send(self, command, flags=socket.CAN_EFF_FLAG):
        self.log.debug('Cmd: {}'.format(str(command)))
        cob_id = c_uint(command.cob_id)
        cob_id.value |= (flags | socket.CAN_RTR_FLAG) if command.request else flags
        can_pkt = self.FORMAT.pack(cob_id.value, len(command.data), command.data)
        self.sock.send(can_pkt)

    def recv(self, flags=0):
        can_pkt = self.sock.recv(72)

        if len(can_pkt) == 16:
            cob_id, length, data = self.FORMAT.unpack(can_pkt)
        else:
            cob_id, length, data = self.FD_FORMAT.unpack(can_pkt)

        cob_id &= socket.CAN_EFF_MASK
        event = CANEvent(cob_id, data[:length])
        self.log.debug('Evt: {}'.format(str(event)))
        return event

    def close(self):
        self.sock.close()
