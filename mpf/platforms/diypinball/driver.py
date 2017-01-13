import logging

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from .can_command import DriverStateCommand, DriverPulseCommand


class Driver(DriverPlatformInterface):
    def __init__(self, platform, config):
        self.log = logging.getLogger('Platform.DIYPinball.Driver')
        self.platform = platform
        self.config = config
        self.number = config['number']
        self.board, self.driver = [int(i) for i in self.number.split('-')]

    def disable(self, coil):
        self.platform.send(DriverStateCommand(self.board, self.driver, False))
        self.platform.log.debug('disable called')

    def enable(self, coil):
        self.platform.send(DriverStateCommand(self.board, self.driver, True))
        self.platform.log.debug('enable called')

    def pulse(self, coil, milliseconds=None):
        if milliseconds is None:
            milliseconds = self.config.get('pulse_ms', 20)
        self.platform.send(DriverPulseCommand(self.board, self.driver, milliseconds))
        self.platform.log.debug('pulse called on {}'.format(self.number))
        return milliseconds
