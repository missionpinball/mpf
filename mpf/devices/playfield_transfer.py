""" Transfer a ball between two playfields. E.g. lower to upper playfield via a ramp"""

import logging
from mpf.system.devices import Device
from mpf.system.config import Config

class PlayfieldTransfer(Device):

    config_section = 'playfield_transfer'
    collection = 'playfield_transfer'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('PlayfieldTransfer.' + name)
        super(PlayfieldTransfer, self).__init__(machine, name, config, collection)

        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize)

    def _initialize(self):
        # register switch handler
        self.machine.switch_controller.add_switch_handler(
            switch_name=self.config['ball_switch'],
            callback=self._ball_went_through,
            state=1, ms=0)
            
        # load target playfield
        self.target = self.machine.ball_devices[self.config['eject_target']]
        self.source = self.machine.ball_devices[self.config['captures_from']]

    def _ball_went_through(self):
        self.log.info("Ball went from " + self.source.name + " to " + self.target.name);

        # source playfield is obviously active
        # we will continue using a callback to keep the ball count sane
        # (otherwise it may go to -1 during the next event)
        self.machine.events.post('sw_' + self.source.name + '_active', callback=self._ball_went_through2)

    # used as callback in _ball_went_through
    def _ball_went_through2(self):
        # trigger remove ball from source playfield
        self.machine.events.post('balldevice_captured_from_' + self.source.name,
                                        balls=1)

        # inform target playfield about incomming ball
        self.machine.events.post('balldevice_' + self.name + '_ball_eject_attempt',
                                        balls=1,
                                        target=self.target,
                                        timeout=0,
                                        callback=self._ball_went_through3)

    # used as callback in _ball_went_through2
    def _ball_went_through3(self, balls, target, timeout):
        # promise (and hope) that it actually goes there
        self.machine.events.post('balldevice_' + self.name + '_ball_eject_success',
                                        balls=1,
                                        target=self.target,
                                        callback=self._ball_went_through4)

    # used as callback in _ball_went_through3
    def _ball_went_through4(self, balls, target):
        # since we confirmed eject target playfield has to be active
        self.machine.events.post('sw_' + self.target.name + '_active')



