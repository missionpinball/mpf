""" Device that handles a multiball """

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device

class Multiball(Device):

    config_section = 'multiballs'
    collection = 'multiballs'
    class_label = 'multiball'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('Multiball.' + name)
        super(Multiball, self).__init__(machine, name, config, collection)

        if 'ball_count' not in self.config:
            raise ValueError('Please specify ball_count')
        if 'source_playfield' not in self.config:
            self.config['source_playfield'] = 'playfield'
        if 'ball_locks' not in self.config:
            self.config['ball_locks'] = []
        else:
            self.config['ball_locks'] = Config.string_to_list(
                self.config['ball_locks'])


        # let ball devices initialise first
        self.machine.events.add_handler('init_phase_3',
                                        self._initialize)

    def _initialize(self):
        self.ball_locks = []
        self.started = False
        self.enabled = False
        for device in self.config['ball_locks']:
            self.ball_locks.append(self.machine.ball_locks[device])

        self.source_playfield = self.machine.ball_devices[self.config['source_playfield']]

        
    def start(self, **kwargs):
        if not self.enabled:
            return

        self.started = True
        self.log.debug("Starting multiball with %s balls",
                       self.config['ball_count'])

        self.balls_ejected = self.config['ball_count'] - 1
        self.machine.game.add_balls_in_play(balls=self.balls_ejected)
        # TODO: use lock_devices first
        self.source_playfield.add_ball(balls=self.balls_ejected)

        # TODO: add handler to drain until self.balls_ejected are drained

    def stop(self, **kwargs):
        self.log.debug("Stopping shoot again of multiball")
        self.stop = False

    def enable(self, **kwargs):
        """ Enables the multiball. If the multiball is not enabled, it cannot
        start.
        """
        self.log.debug("Enabling...")
        self.enabled = True

    def disable(self, **kwargs):
        """ Disabless the multiball. If the multiball is not enabled, it cannot
        start.
        """
        self.log.debug("Disabling...")
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the multiball and disables it.
        """
        self.enabled = False
        self.started = False


