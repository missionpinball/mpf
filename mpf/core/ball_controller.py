"""Contains the BallController class which manages and tracks all the balls in a pinball machine."""

import logging

from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util


class BallController(object):

    """Base class for the Ball Controller which is used to keep track of all the balls in a pinball machine.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.
    """

    def __init__(self, machine):
        """Initialise ball controller."""
        self.machine = machine
        self.log = logging.getLogger("BallController")
        self.log.debug("Loading the BallController")
        self.delay = DelayManager(self.machine.delayRegistry)

        self.num_balls_known = -999

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)
        self.machine.events.add_handler('machine_reset_phase_2',
                                        self._initialize)
        self.machine.events.add_handler('init_phase_2',
                                        self._init2)

    def _init2(self):
        # register a handler for all switches
        for device in self.machine.ball_devices:
            if 'ball_switches' not in device.config:
                continue
            for switch in device.config['ball_switches']:
                self.machine.switch_controller.add_switch_handler(switch.name,
                                                                  self._update_num_balls_known,
                                                                  ms=device.config['entrance_count_delay'],
                                                                  state=1)
                self.machine.switch_controller.add_switch_handler(switch.name,
                                                                  self._update_num_balls_known,
                                                                  ms=device.config['exit_count_delay'],
                                                                  state=0)
                self.machine.switch_controller.add_switch_handler(switch.name,
                                                                  self._correct_playfield_count,
                                                                  ms=device.config['entrance_count_delay'],
                                                                  state=1)
                self.machine.switch_controller.add_switch_handler(switch.name,
                                                                  self._correct_playfield_count,
                                                                  ms=device.config['exit_count_delay'],
                                                                  state=0)

        for playfield in self.machine.playfields:
            self.machine.events.add_handler('{}_ball_count_change'.format(playfield.name),
                                            self._correct_playfield_count)

        # run initial count
        self._update_num_balls_known()

    def _get_loose_balls(self):
        return self.num_balls_known - self._count_stable_balls()

    def _count_stable_balls(self):
        self.log.debug("Counting Balls")
        balls = 0

        for device in self.machine.ball_devices:
            if device.is_playfield():
                continue

            if not device.is_ball_count_stable():
                raise ValueError("devices not stable")

            # generally we do not count ball devices without switches
            if 'ball_switches' not in device.config:
                continue
            # special handling for troughs (needed for gottlieb)
            elif not device.config['ball_switches'] and 'trough' in device.tags:
                balls += device.balls
            else:
                for switch in device.config['ball_switches']:
                    if self.machine.switch_controller.is_active(
                            switch.name, ms=device.config['entrance_count_delay']):
                        balls += 1
                    elif self.machine.switch_controller.is_inactive(
                            switch.name, ms=device.config['exit_count_delay']):
                        continue
                    else:
                        raise ValueError("switches not stable")

        return balls

    def _correct_playfield_count(self, **kwargs):
        del kwargs
        self.delay.reset(ms=1, callback=self._correct_playfield_count2, name="correct_playfield")

    def _correct_playfield_count2(self):
        try:
            loose_balls = self._get_loose_balls()
        except ValueError:
            self.delay.reset(ms=10000, callback=self._correct_playfield_count2, name="correct_playfield")
            return

        balls_on_pfs = 0

        for playfield in self.machine.playfields:
            balls_on_pfs += playfield.balls

        jump_sources = []
        jump_targets = []

        # fix too much balls and prefer playfields where balls and available_balls have the same value
        if balls_on_pfs > loose_balls:
            balls_on_pfs -= self._fix_jumped_balls(balls_on_pfs - loose_balls, jump_sources)

        # fix too much balls and take the remaining playfields
        if balls_on_pfs > loose_balls:
            balls_on_pfs -= self._remove_balls_from_playfield_randomly(balls_on_pfs - loose_balls, jump_sources)

        if balls_on_pfs > loose_balls:
            self.log.warning("Failed to remove enough balls from playfields. This is a bug!")

        for playfield in self.machine.playfields:
            if playfield.balls != playfield.available_balls:
                self.log.warning("Corecting available_balls %s to %s on playfield %s",
                                 playfield.available_balls, playfield.balls, playfield.name)
                if playfield.balls > playfield.available_balls:
                    jump_targets.append(playfield)
                playfield.available_balls = playfield.balls

        for _ in range(min(len(jump_sources), len(jump_targets))):
            source = jump_sources.pop()
            target = jump_targets.pop()
            self.log.warning("Suspecting that ball jumped from {} to {}".format(str(source), str(target)))
            self.machine.events.post("playfield_jump", source=source, target=target)

    def _fix_jumped_balls(self, balls_to_remove, jump_sources):
        balls_removed = 0
        for dummy_i in range(balls_to_remove):
            for playfield in self.machine.playfields:
                self.log.warning("Corecting balls on pf from %s to %s on playfield %s (preferred)",
                                 playfield.balls, playfield.balls - 1, playfield.name)
                if playfield.available_balls == playfield.balls and playfield.balls > 0:
                    jump_sources.append(playfield)
                    if playfield.unexpected_balls > 0:
                        playfield.unexpected_balls -= 1
                    playfield.balls -= 1
                    playfield.available_balls -= 1
                    balls_removed += 1
                    break
        return balls_removed

    def _remove_balls_from_playfield_randomly(self, balls_to_remove, jump_sources):
        balls_removed = 0
        for dummy_i in range(balls_to_remove):
            for playfield in self.machine.playfields:
                self.log.warning("Corecting balls on pf from %s to %s on playfield %s",
                                 playfield.balls, playfield.balls - 1, playfield.name)
                if playfield.balls > 0:
                    jump_sources.append(playfield)
                    if playfield.unexpected_balls > 0:
                        playfield.unexpected_balls -= 1
                    playfield.balls -= 1
                    playfield.available_balls -= 1
                    balls_removed += 1
                    break
        return balls_removed

    def trigger_ball_count(self):
        """Count the balls now if possible."""
        self._update_num_balls_known()
        self._correct_playfield_count()

    def _update_num_balls_known(self):
        try:
            balls = self._count_balls()
        except ValueError:
            self.delay.reset(ms=100, callback=self._update_num_balls_known, name="update_num_balls_known")
            return

        if self.num_balls_known < 0:
            self.num_balls_known = 0
        if balls > self.num_balls_known:
            self.log.debug("Found new balls. Setting known balls to %s", balls)
            self.delay.add(1, self._handle_new_balls, new_balls=balls - self.num_balls_known)
            self.num_balls_known = balls

    def _handle_new_balls(self, new_balls):
        for dummy_i in range(new_balls):
            for playfield in self.machine.playfields:
                if playfield.unexpected_balls > 0:
                    playfield.unexpected_balls -= 1
                    playfield.available_balls += 1
                    break

    def _count_balls(self):
        self.log.debug("Counting Balls")
        balls = 0

        for device in self.machine.ball_devices:
            # generally we do not count ball devices without switches
            if 'ball_switches' not in device.config:
                continue
            # special handling for troughs (needed for gottlieb)
            elif not device.config['ball_switches'] and 'trough' in device.tags:
                balls += device.balls
            else:
                for switch in device.config['ball_switches']:
                    if self.machine.switch_controller.is_active(
                            switch.name, ms=device.config['entrance_count_delay']):
                        balls += 1
                    elif self.machine.switch_controller.is_inactive(
                            switch.name, ms=device.config['exit_count_delay']):
                        continue
                    else:
                        raise ValueError("switches not stable")

        return balls

    def _initialize(self):

        # If there are no ball devices, then the ball controller has no work to
        # do and will create errors, so we just abort.
        if not hasattr(self.machine, 'ball_devices'):
            return

        for device in self.machine.ball_devices:
            if 'drain' in device.tags:  # device is used to drain balls from pf
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_enter',
                                                self._ball_drained_handler)

    def request_to_start_game(self):
        """Method registered for the *request_to_start_game* event.

        Checks to make sure that the balls are in all the right places and
        returns. If too many balls are missing (based on the config files 'Min
        Balls' setting), it will return False to reject the game start request.
        """
        try:
            balls = self._count_balls()
        except ValueError:
            balls = -1
        self.log.debug("Received request to start game.")
        self.log.debug("Balls contained: %s, Min balls needed: %s",
                       balls,
                       self.machine.config['machine']['min_balls'])
        if balls < self.machine.config['machine']['min_balls']:
            self.log.warning("BallController denies game start. Not enough "
                             "balls")
            return False

        if self.machine.config['game']['allow_start_with_ball_in_drain']:
            allowed_positions = ['home', 'trough', 'drain']
        else:
            allowed_positions = ['home', 'trough']

        if self.machine.config['game']['allow_start_with_loose_balls']:
            return

        elif not self.are_balls_collected(allowed_positions):
            self.collect_balls('home')
            self.log.warning("BallController denies game start. Balls are not "
                             "in their home positions.")
            return False

    def are_balls_collected(self, target):
        """Check to see if all the balls are contained in devices tagged with the parameter that was passed.

        Note if you pass a target that's not used in any ball devices, this
        method will return True. (Because you're asking if all balls are
        nowhere, and they always are. :)

        Args:
            target: String or list of strings of the tags you'd like to
                collect the balls to. Default of None will be replaced with
                'home' and 'trough'.
        """
        self.log.debug("Checking to see if all the balls are in devices tagged"
                       " with '%s'", target)

        if isinstance(target, str):
            target = Util.string_to_list(target)

        count = 0
        devices = set()

        for tag in target:
            for device in self.machine.ball_devices.items_tagged(tag):
                devices.add(device)

        if len(devices) == 0:
            # didn't find any devices matching that tag, so we return True
            return True

        for device in devices:
            count += device.get_status('balls')
            self.log.debug('Found %s ball(s) in %s. Found %s total',
                           device.get_status('balls'), device.name, count)

        if count == self.machine.ball_controller.num_balls_known:
            self.log.debug("Yes, all balls are collected")
            return True
        else:
            self.log.debug("No, all balls are not collected. Balls Counted: %s. "
                           "Total balls known: %s", count,
                           self.machine.ball_controller.num_balls_known)
            return False

    def collect_balls(self, target='home, trough'):
        """Used to ensure that all balls are in contained in ball devices with the tag or list of tags you pass.

        Typically this would be used after a game ends, or when the machine is
        reset or first starts up, to ensure that all balls are in devices
        tagged with 'home' and/or 'trough'.

        Args:
            target: A string of the tag name or a list of tags names of the
                ball devices you want all the balls to end up in. Default is
                ['home', 'trough'].

        """
        tag_list = Util.string_to_list(target)

        self.log.debug("Collecting all balls to devices with tags '%s'",
                       tag_list)

        target_devices = set()
        source_devices = set()
        balls_to_collect = False

        for tag in tag_list:
            for device in self.machine.ball_devices.items_tagged(tag):
                target_devices.add(device)

        for device in self.machine.ball_devices:
            if device not in target_devices:
                if device.available_balls:
                    source_devices.add(device)
                    balls_to_collect = True

        self.log.debug("Ejecting all balls from: %s", source_devices)

        if balls_to_collect:
            self.machine.events.post('collecting_balls')
            '''event: collecting_balls

            desc: Posted by the ball controller when it starts the collecting
                balls process.

            '''

            for device in target_devices:
                self.machine.events.replace_handler(
                    'balldevice_{}_ball_enter'.format(device.name),
                    self._collecting_balls_entered_callback,
                    target=target)

            for device in source_devices:
                if not device.is_playfield():
                    device.eject_all()
        else:
            self.log.debug("All balls are collected")
            self._collecting_balls_complete()

    def _collecting_balls_entered_callback(self, target, new_balls, unclaimed_balls, **kwargs):
        del kwargs
        del new_balls
        if self.are_balls_collected(target=target):
            self._collecting_balls_complete()

        return {'unclaimed_balls': unclaimed_balls}

    def _collecting_balls_complete(self):
        self.machine.events.remove_handler(self._collecting_balls_complete)
        self.machine.events.post('collecting_balls_complete')
        '''event: collecting_balls_complete

        desc: Posted by the ball controller when it has finished the collecting
            balls process.

        '''

    def _ball_drained_handler(self, new_balls, unclaimed_balls, device, **kwargs):
        del kwargs
        del new_balls
        self.machine.events.post_relay('ball_drain',
                                       callback=self._process_ball_drained,
                                       device=device,
                                       balls=unclaimed_balls)
        '''event: ball_drain

        desc: A ball (or balls) has just drained. (More specifically, ball(s)
        have entered a ball device tagged with "drain".)

        This is a relay event.

        args:

        device: The ball device object that received the ball(s)

        balls: The number of balls that have just drained. Any balls remaining
        after the relay will be processed as newly-drained balls.

        '''

        # What happens if the ball enters the trough but the ball_add_live
        # event hasn't confirmed its eject? todo

    def _process_ball_drained(self, balls=None, ev_result=None, **kwargs):
        # We don't need to do anything here because other modules (ball save,
        # the game, etc. should jump in and do whatever they need to do when a
        # ball is drained.
        pass
