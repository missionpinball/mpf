import logging

from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from .can_command import MatrixLightCommand


class MatrixLight(MatrixLightPlatformInterface):
    def __init__(self, platform, config):
        self.log = logging.getLogger('Platform.DIYPinball.MatrixLight')
        self.platform = platform
        self.config = config
        self.number = config['number']
        self.board, self.light = [int(i) for i in self.number.split('-')]

    def on(self, brightness=255):
        self.platform.send(MatrixLightCommand(self.board, self.light, brightness))

    def off(self):
        self.platform.send(MatrixLightCommand(self.board, self.light, 0))
