""" Device that implements a ball save """

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.config import Config

class BallSave(Device):

    config_section = 'ball_saves'
    collection = 'ball_saves'
    class_label = 'ball_save'

    def __init__(self, machine, name, config, collection=None):

        self.log = logging.getLogger('BallSave.' + name)
        super(BallSave, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        self.source_playfield = self.config['source_playfield']

    def enable(self, **kwargs):
        self.log.debug("Enabling...")

        # Enable shoot again
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_shoot_again,
                                        priority=1000)

        if self.config['auto_disable_time'] > 0:
            self.delay.add('disable_shoot_again',
                           self.config['auto_disable_time'], self.disable)

        self.machine.events.post('ball_save_' + self.name + '_enabled')

    def disable(self, **kwargs):
        self.log.debug("Disabling...")
        self.machine.events.remove_handler(self._ball_drain_shoot_again)
        self.delay.remove('disable_shoot_again')

        self.machine.events.post('ball_save_' + self.name + '_disabled')

    def _ball_drain_shoot_again(self, balls, **kwargs):
        if balls <= 0:
            return {'balls': balls}

        self.machine.events.post("ball_save_" + self.name + "_shoot_again", balls=balls)

        self.log.debug("Ball drained during ball save. Requesting a new one.")
        self.source_playfield.add_ball(balls=balls)
        return {'balls': 0}
