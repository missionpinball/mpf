import struct

from .feature import Feature


class CANEvent(object):
    def __init__(self, cob_id=None, data=None):
        if cob_id is not None:
            self.decode(cob_id)
        self.data = data

    def decode(self, cob_id):
        self.prio = (cob_id >> 25) & 0x0f
        self.board_specific = True if (cob_id & 0x01000000) else False
        self.board = (cob_id >> 16) & 0xff
        self.feature_type = Feature((cob_id >> 12) & 0x0f)
        self.feature_number = (cob_id >> 8) & 0x0f
        self.msg_type = (cob_id >> 4) & 0x0f

    @property
    def hw_id(self):
        return '{}-{}'.format(self.board, self.feature_number)

    def __str__(self):
        return 'Board: {0}, Feature: {1}, Number: {2}'.format(self.board, self.feature_type.name, self.feature_number)
