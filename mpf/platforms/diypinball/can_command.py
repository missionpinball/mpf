import struct

from .feature import Feature


class CANCommand(object):
    def __init__(self, board, device):
        self.prio = 0
        self.board_specific = True
        self.board = board
        self.feature_type = Feature.system
        self.feature_number = device
        self.msg_type = 0
        self.data = b''
        self.request = False

    @property
    def cob_id(self):
        cob_id = 0
        cob_id |= (self.prio & 0x0f) << 25
        bs = 1 if self.board_specific else 0
        cob_id |= bs << 24
        cob_id |= (self.board & 0xff) << 16
        cob_id |= (self.feature_type.value & 0x0f) << 12
        cob_id |= (self.feature_number & 0x0f) << 8
        cob_id |= (self.msg_type & 0x0f) << 4
        return cob_id

    def __str__(self):
        return 'P: {}, BS: {}, B: {}, FT: {}, FN: {}, MT: {}, D: {}'.format(self.prio,
                                                                            self.board_specific,
                                                                            self.board,
                                                                            self.feature_type,
                                                                            self.feature_number,
                                                                            self.msg_type,
                                                                            repr(self.data))


class DriverStateCommand(CANCommand):
    def __init__(self, board, driver, state):
        super(DriverStateCommand, self).__init__(board, driver)
        self.feature_type = Feature.driver
        state = 1 if state else 0
        self.data = struct.pack('B', state)


class DriverPulseCommand(CANCommand):
    def __init__(self, board, driver, milliseconds):
        super(DriverPulseCommand, self).__init__(board, driver)
        self.feature_type = Feature.driver
        self.data = struct.pack('BB', 1, milliseconds)


class MatrixLightCommand(CANCommand):
    def __init__(self, board, light, brightness):
        super(MatrixLightCommand, self).__init__(board, light)
        self.feature_type = Feature.lamp
        self.data = struct.pack('B', brightness)


class ScoreSetCommand(CANCommand):
    def __init__(self, board, score):
        super(ScoreSetCommand, self).__init__(board, 0)
        self.feature_type = Feature.score_display
        self.msg_type = 0
        self.data = struct.pack('>i', score)


class SwitchRequestStatusCommand(CANCommand):
    def __init__(self, board, switch):
        super(SwitchRequestStatusCommand, self).__init__(board, switch)
        self.feature_type = Feature.switch
        self.msg_type = 0
        self.request = True


class TextSetCommand(CANCommand):
    character_lut = {
        ' ': 0x00,
        'a': 0x77,
        'b': 0x1F,
        'c': 0x4E,
        'e': 0x4F,
        'g': 0x7B,
        'i': 0x06,
        'l': 0x0E,
        'o': 0x7E,
        'p': 0x67,
        'r': 0x05,
        's': 0x5B,
        'u': 0x1C,
        'v': 0x1C,
        'y': 0x3B,
        '.': 0x80
    }

    def __init__(self, board, text):
        super(TextSetCommand, self).__init__(board, 0)
        self.feature_type = Feature.score_display
        self.msg_type = 2
        self.data = self.convert_text(text)

    def convert_text(self, text):
        return bytes(self.character_lut[char] for char in text)
