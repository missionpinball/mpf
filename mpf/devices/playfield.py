"""Contains the Playfield device class which represents the actual playfield in
a pinball machine."""

import logging

from mpf.devices.ball_device import BallDevice
from mpf.system.ball_search import BallSearch
from mpf.system.tasks import DelayManager


class Playfield(BallDevice):

    config_section = 'playfields'
    collection = 'playfields'
    class_label = 'playfield'

    # noinspection PyMissingConstructor
    def __init__(self, machine, name, config, collection=None, validate=True):
        self.log = logging.getLogger('playfield')

        self.machine = machine
        self.name = name.lower()
        self.tags = list()
        self.label = None
        self.debug = False
        self.config = dict()
        self.unexpected_balls = 0
        self.ball_search = BallSearch(self.machine, self)

        if validate:
            self.config = self.machine.config_processor.process_config2(
                self.config_section, config, self.name)
        else:
            self.config = config

        if self.config['debug']:
            self.debug = True
            self.log.debug("Enabling debug logging for this device")
            self.log.debug("Configuring device with settings: '%s'", config)

        self.tags = self.config['tags']
        self.label = self.config['label']

        self.delay = DelayManager(self.machine.delayRegistry)

        self.machine.ball_devices[name] = self

        if 'default' in self.config['tags']:
            self.machine.playfield = self

        # Attributes
        self._balls = 0
        self.available_balls=0
        self.num_balls_requested = 0
        self.queued_balls = list()
        self._playfield = True

        # Set up event handlers

        # Watch for balls added to the playfield
        for device in self.machine.ball_devices:
            for target in device.config['eject_targets']:
                if target == self.name:
                    self.machine.events.add_handler(
                        event='balldevice_' + device.name +
                        '_ball_eject_success',
                        handler=self._source_device_eject_success)
                    self.machine.events.add_handler(
                        event='balldevice_' + device.name +
                        '_ball_eject_failed',
                        handler=self._source_device_eject_failed)
                    self.machine.events.add_handler(
                        event='balldevice_' + device.name +
                        '_ball_eject_attempt',
                        handler=self._source_device_eject_attempt)
                    break

        # Watch for balls removed from the playfield
        self.machine.events.add_handler('balldevice_captured_from_' + self.name,
                                        self._ball_removed_handler)

        # Watch for any switch hit which indicates a ball on the playfield
        self.machine.events.add_handler('sw_' + self.name + '_active',
                                        self.playfield_switch_hit)

        self.machine.events.add_handler('init_phase_2',
                                        self._initialize)

    def _initialize(self):
        self.ball_controller = self.machine.ball_controller

        for device in self.machine.playfield_transfers:
            if device.config['eject_target'] == self:
                self.machine.events.add_handler(
                    event='balldevice_' + device.name +
                    '_ball_eject_success',
                    handler=self._source_device_eject_success)
                self.machine.events.add_handler(
                    event='balldevice_' + device.name +
                    '_ball_eject_attempt',
                    handler=self._source_device_eject_attempt)

    def add_missing_balls(self, balls):
        # if we catched an unexpected balls before do not add a ball
        if self.unexpected_balls:
            self.unexpected_balls -= 1
            balls -= 1

        self.balls += balls
        self.available_balls += balls

    @property
    def balls(self):
        return self._balls

    @balls.setter
    def balls(self, balls):

        prior_balls = self._balls
        ball_change = balls - prior_balls

        if ball_change:
            self.log.debug("Ball count change. Prior: %s, Current: %s, Change:"
                           " %s", prior_balls, balls, ball_change)

        if balls >= 0:
            self._balls = balls
        else:
            self.log.warning("Playfield balls went to %s. Resetting to 0, but "
                             "FYI that something's weird", balls)
            self._balls = 0
            self.unexpected_balls = 0

        self.log.debug("New Ball Count: %s. (Prior count: %s)",
                       self._balls, prior_balls)

        if ball_change > 0:
            self.machine.events.post_relay('balldevice_' + self.name +
                                           '_ball_enter', new_balls=ball_change,
                                           unclaimed_balls=ball_change,
                                           device=self)

        if ball_change:
            self.machine.events.post(self.name + '_ball_count_change',
                                     balls=balls, change=ball_change)

        if balls <= 0:
            self.ball_search.disable()
        else:
            self.ball_search.enable()

    def count_balls(self, **kwargs):
        """Used to count the number of balls that are contained in a ball
        device. Since this is the playfield device, this method always returns
        zero.

        Returns: 0

        """
        return 0

    def get_additional_ball_capacity(self):
        """Used to find out how many more balls this device can hold. Since this
        is the playfield device, this method always returns 999.

        Returns: 999

        """
        return 999

    def add_ball(self, balls=1, source_device=None,
                 player_controlled=False, reset=False):
        """Adds live ball(s) to the playfield.

        Args:
            balls: Integer of the number of balls you'd like to add.
            source_device: Optional ball device object you'd like to add the
                ball(s) from.
            player_controlled: Boolean which specifies whether this event is
                player controlled. (See not below for details)
            reset: Boolean which controls whether the source device should
                reset its state to idle

        Returns:
            True if it's able to process the add_ball() request, False if it
            cannot.

        The source_device arg is included to give you an options for specifying
        the source of the ball(s) to be added. This argument is optional, so if
        you don't supply them then MPF will look for a device
        tagged with 'ball_add_live'. If you don't provide a source and you don't
        have a device with the 'ball_add_live' tag, MPF will quit.

        This method does *not* increase the game controller's count of the
        number of balls in play. So if you want to add balls (like in a
        multiball scenario), you need to call this method along with
        ``self.machine.game.add_balls_in_play()``.)

        MPF tracks the number of balls in play separately from the actual balls
        on the playfield because there are numerous situations where the two
        counts are not the same. For example, if a ball is in a VUK while some
        animation is playing, there are no balls on the playfield but still one
        ball in play, or if the player has a two-ball multiball and they shoot
        them both into locks, there are still two balls in play even though
        there are no balls on the playfield. The opposite can also be true,
        like when the player tilts then there are still balls on the playfield
        but no balls in play.

        Explanation of the player_controlled parameter:

        Set player_controlled to True to indicate that MPF should wait for the
        player to eject the ball from the source_device rather than firing a
        coil. The logic works like this:

        If the source_device does not have an eject_coil defined, then it's
        assumed that player_controlled is the only option. (e.g. this is a
        traditional plunger.) If the source_device does have an eject_coil
        defined, then there are two ways the eject could work. (1) there could
        be a "launch" button of some kind that's used to fire the eject coil,
        or (2) the device could be the auto/manual combo style where there's a
        mechanical plunger but also a coil which can eject the ball.

        If player_controlled is true and the device has an eject_coil, MPF will
        look for the player_controlled_eject_tag and eject the ball when a
        switch with that tag is activated.

        If there is no player_controlled_eject_tag, MPF assumes it's a manual
        plunger and will wait for the ball to disappear from the device based
        on the device's ball count decreasing.

        """
        if balls == 0:
            return False
        elif balls < 0:
            raise AssertionError("Received request to add negative balls, which "
                                 "doesn't  make sense. Not adding any balls...")

        # Figure out which device we'll get a ball from

        if source_device:
            pass
        else:
            for device in self.machine.ball_devices.items_tagged('ball_add_live'):
                if self in device.config['eject_targets']:
                    source_device = device
                    break

        if not source_device:
            self.log.critical("Received request to add a ball to the playfield"
                              ", but no source device was passed and no ball "
                              "devices are tagged with 'ball_add_live'. Cannot"
                              " add a ball.")
            return False

        if reset:
            source_device.stop()

        self.log.debug("Received request to add %s ball(s). Source device: %s."
                       " Player-controlled: %s", balls,
                       source_device.name, player_controlled)

        if player_controlled:
            source_device.setup_player_controlled_eject(balls=balls,
                                                        target=self)
        else:
            source_device.eject(balls=balls, target=self, get_ball=True)

        return True

    def mark_playfield_active(self):
        self.ball_search.reset_timer()
        self.machine.events.post_boolean(self.name + "_active")

    def playfield_switch_hit(self, **kwargs):
        """A switch tagged with '<this playfield name>_active' was just hit,
        indicating that there is at least one ball on the playfield.

        """
        if (not self.balls or (kwargs.get('balls') and self.balls - kwargs['balls'] < 0)):
            self.mark_playfield_active()

            if not self.num_balls_requested:
                if self.machine.game:
                    self.unexpected_balls = 1

                if self.machine.config['machine']['glass_off_mode']:
                    self.log.debug("Playfield_active switch hit with no balls "
                                   "expected. glass_off_mode is enabled, so "
                                   "this will be ignored.")
                else:
                    self.log.debug("Playfield_active switch hit with no balls "
                                   "expected. glass_off_mode is not enabled, "
                                   "setting playfield ball count to 1")

                    self.balls = 1
                    self.machine.events.post('unexpected_ball_on_' + self.name)

    def _ball_removed_handler(self, balls, **kwargs):
        # somebody got a ball from us so we obviously had one
        self.machine.events.post('sw_' + self.name + "_active",
                callback=self._ball_removed_handler2, balls=balls)

    def _ball_removed_handler2(self, balls):
        self.log.debug("%s ball(s) removed from the playfield", balls)
        self.balls -= balls
        self.available_balls -= balls
        if self.available_balls < 0:
            self.available_balls = 0

    def _source_device_eject_attempt(self, balls, target, **kwargs):
        # A source device is attempting to eject a ball. We need to know if it's
        # headed to the playfield.
        if target == self:
            self.log.debug("A source device is attempting to eject %s ball(s)"
                           " to the playfield.", balls)
            self.num_balls_requested += balls

    def _source_device_eject_failed(self, balls, target, **kwargs):
        # A source device failed to eject a ball. We need to know if it was
        # headed to the playfield.
        if target == self:
            self.log.debug("A source device has failed to eject %s ball(s)"
                           " to the playfield.", balls)
            self.num_balls_requested -= balls

    def _source_device_eject_success(self, balls, target):
        # A source device has just confirmed that it has successfully ejected a
        # ball. Note that we don't care what type of confirmation it used.
        # (Playfield switch hit, count of its ball switches, etc.)

        if target == self:
            self.log.debug("A source device has confirmed it's ejected %s "
                           "ball(s) to the playfield.", balls)
            self.balls += balls
            self.num_balls_requested -= balls

            if self.num_balls_requested < 0:
                raise Exception("num_balls_requested is smaller 0, which doesn't make "
                                "sense. Quitting...")

    def eject(self, *args, **kwargs):
        pass

    def eject_all(self, *args, **kwargs):
        pass

    def is_playfield(self):
        return True

    def add_incoming_ball(self, source):
        pass

    def remove_incoming_ball(self, source):
        pass
