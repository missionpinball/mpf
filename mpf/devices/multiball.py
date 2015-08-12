""" Device that handles a multiball """

# Documentation and more info at http://missionpinball.com/mpf

import logging
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.config import Config

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
        if 'shoot_again' not in self.config:
            self.config['shoot_again'] = '10s'
        if 'ball_locks' not in self.config:
            self.config['ball_locks'] = []
        else:
            self.config['ball_locks'] = Config.string_to_list(
                self.config['ball_locks'])

        if not isinstance(self.config['shoot_again'], bool):
            self.config['shoot_again'] = Timing.string_to_ms(self.config['shoot_again'])

        self.delay = DelayManager()

        # let ball devices initialise first
        self.machine.events.add_handler('init_phase_3',
                                        self._initialize)

    def _initialize(self):
        self.ball_locks = []
        self.shoot_again = False
        self.enabled = False

        for device in self.config['ball_locks']:
            self.ball_locks.append(self.machine.ball_locks[device])

        self.source_playfield = self.machine.ball_devices[self.config['source_playfield']]

        
    def start(self, **kwargs):
        if not self.enabled:
            return



        if self.balls_ejected > 0:
            self.log.debug("Cannot start MB because %s are still in play",
                           self.balls_ejected)

        self.shoot_again = True
        self.log.debug("Starting multiball with %s balls",
                       self.config['ball_count'])

        self.balls_ejected = self.config['ball_count'] - 1

        self.machine.game.add_balls_in_play(balls=self.balls_ejected)

        balls_added = 0

        # use lock_devices first
        for device in self.ball_locks:
            balls_added += device.release_balls(self.balls_ejected - balls_added)

            if self.balls_ejected - balls_added <= 0:
                break

        # request remaining balls
        if self.balls_ejected - balls_added > 0:
            self.source_playfield.add_ball(balls=self.balls_ejected - balls_added)

        if self.config['shoot_again'] == False:
            # No shoot again. Just stop multiball right away
            self.stop()
        else:
            # Enable shoot again
            self.machine.events.add_handler('ball_drain',
                                            self._ball_drain_shoot_again,
                                            priority=1000)
            # Register stop handler
            if not isinstance(self.config['shoot_again'], bool):
                self.delay.add('disable_shoot_again',
                               self.config['shoot_again'], self.stop)

        self.machine.events.post("multiball_" + self.name + "_started",
                         balls=self.config['ball_count'])

    def _ball_drain_shoot_again(self, balls, **kwargs):
        if balls <= 0:
            return {'balls': balls}

        self.machine.events.post("multiball_" + self.name + "_shoot_again", balls=balls)

        self.log.debug("Ball drained during MB. Requesting a new one")
        self.source_playfield.add_ball(balls=balls)
        return {'balls': 0}


    def _ball_drain_count_balls(self, balls, **kwargs):
        self.balls_ejected -= balls
        if self.balls_ejected <= 0:
            self.balls_ejected = 0
            self.machine.events.remove_handler(self._ball_drain_count_balls)
            self.machine.events.post("multiball_" + self.name + "_ended")
            self.log.debug("Ball drained. MB ended.")
        else:
            self.log.debug("Ball drained. %s balls remain until MB ends",
                           self.balls_ejected)

        # TODO: we are _not_ claiming the balls because we want it to drain.
        # However this may result in wrong results with multiple MBs at the
        # same time. May be we should claim and remove balls manually?

        return {'balls': balls}

    def stop(self, **kwargs):
        self.log.debug("Stopping shoot again of multiball")
        self.shoot_again = False

        # disable shoot again
        self.machine.events.remove_handler(self._ball_drain_shoot_again)

        # add handler for ball_drain until self.balls_ejected are drained
        self.machine.events.add_handler('ball_drain',
                                        self._ball_drain_count_balls)

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
        self.shoot_again = False
        self.balls_ejected = 0

