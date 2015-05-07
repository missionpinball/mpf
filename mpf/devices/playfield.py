"""Contains the Playfield device class which represents the actual playfield in
a pinball machine."""
# playfield.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

import logging
from collections import defaultdict
import sys

from mpf.devices.ball_device import BallDevice
from mpf.system.tasks import DelayManager


class Playfield(BallDevice):

    def __init__(self, machine, name, collection):
        self.log = logging.getLogger('Playfield')

        self.machine = machine
        self.name = name
        self.tags = list()
        self.config = defaultdict(lambda: None)
        self.config['eject_targets'] = list()

        self.ball_controller = self.machine.ball_controller

        self.delay = DelayManager()

        # Add the playfield ball device to the existing device collection
        collection_object = getattr(self.machine, collection)[name] = self

        # Attributes
        self._balls = 0
        self.num_balls_requested = 0

        # Set up event handlers

        # Watch for balls added to the playfield
        for device in self.machine.balldevices:
            for target in device.config['eject_targets']:
                if target == self.name:
                    self.machine.events.add_handler(
                        event='balldevice_' + device.name +
                        '_ball_eject_success',
                        handler=self._source_device_eject_success)
                    self.machine.events.add_handler(
                        event='balldevice_' + device.name +
                        '_ball_eject_attempt',
                        handler=self._source_device_eject_attempt)
                break

        # Watch for balls removed from the playfield
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._ball_removed_handler)

        # Watch for any switch hit which indicates a ball on the playfield
        self.machine.events.add_handler('sw_playfield_active',
                                        self.playfield_switch_hit)

    @property
    def balls(self):
        return self._balls

    @balls.setter
    def balls(self, balls):

        prior_balls = self._balls
        ball_change = balls - prior_balls

        if ball_change:
            self.log.debug("Ball count change. Prior: %s, Current: %s, Change: "
                           "%s", prior_balls, balls, ball_change)

        if balls > 0:
            self._balls = balls
            #self.ball_search_schedule()
        elif balls == 0:
            self._balls = 0
            #self.ball_search_disable()
        else:
            self.log.warning("Playfield balls went to %s. Resetting to 0, but "
                             "FYI that something's weird", balls)
            self._balls = 0
            #self.ball_search_disable()

        self.log.debug("New Ball Count: %s. (Prior count: %s)",
                       self._balls, prior_balls)

        if ball_change > 0:
            self.machine.events.post_relay('balldevice_' + self.name +
                                           '_ball_enter', balls=ball_change)

        if ball_change:
            self.machine.events.post('playfield_ball_count_change',
                                     balls=balls, change=ball_change)

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

    def add_ball(self, balls=1, source_name=None, source_device=None,
                 trigger_event=None):

        """Adds live ball(s) to the playfield.

        Args:
            balls: Integer of the number of balls you'd like to add.
            source_name: Optional string name of the ball device you'd like to
                add the ball(s) from.
            source_device: Optional ball device object you'd like to add the
                ball(s) from.
            trigger_event: The optional name of an event that MPF will wait for
                before adding the ball into play. Typically used with player-
                controlled eject tag events.

        Both source_name and source_device args are included to give you two
        options for specifying the source of the ball(s) to be added. You don't
        need to supply both. (it's an "either/or" thing.) Both of these args are
        optional, so if you don't supply them then MPF will look for a device
        tagged with 'ball_add_live'. If you don't provide a source and you don't
        have a device with the 'ball_add_live' tag, MPF will quit.

        This method does *not* increase the game controller's count of the
        number of balls in play. So if you want to add balls (like in a
        ball scenario(, you need to call this method along with
        ``self.machine.game.add_balls_in_play()``.)

        MPF tracks the number of balls in play separately from the actual balls
        on the playfield because there are numerous situations where the two
        counts are not the same. For example, if a ball is in a VUK while some
        animation is playing, there are no balls on the playfield but still one
        ball in play, or if the player has a two-ball multiball and they shoot
        them both into locks, there are still two balls in play even though
        there are no balls on the playfield, or if the player tilts then there
        are still balls on the playfield but no balls in play.

        """

        if balls < 1:
            self.log.error("Received request to add %s balls, which doesn't "
                           "make sense. Quitting...")
            raise Exception("Received request to add %s balls, which doesn't "
                            "make sense. Quitting...")

        # Figure out which device we'll get a ball from

        if source_device:
            pass
        elif source_name and source_name in self.machine.balldevices:
            source_device = self.machine.balldevices[source_name]
        else:
            for device in self.machine.balldevices.items_tagged('ball_add_live'):
                source_device = device
                break

        if not source_device:
            self.log.critical("Received request to add a ball to the playfield, "
                              "but no source device was passed and no ball "
                              "devices are tagged with 'ball_add_live'. Cannot "
                              "add a ball.")
            raise Exception("Received request to add a ball to the playfield, "
                            "but no source device was passed and no ball "
                            "devices are tagged with 'ball_add_live'. Cannot "
                            "add a ball.")

        self.log.debug("Received request to add %s ball(s). Source device: %s. "
                       "Wait for event: %s", balls, source_device.name,
                       trigger_event)

        # If we don't have a coil that's fired by the player, and we our source
        # device has the ability to eject, then we do the eject now.

        # Some examples:

        # Plunger lane w/ switch and coil: ball_add_live device is plunger lane,
        # we don't eject now since *not* player_controlled is true.

        # Plunger lane w/ switch. No coil: ball_add_live device is plunger lane,
        # we don't eject now since there's no eject_coil for that device.

        # Plunger lane has no switch: ball_add_live device is trough, we do
        # eject now since there's no player_controlled tag and the device has an
        # eject coil.

        if not trigger_event and source_device.config['eject_coil']:
            source_device.eject(balls=balls, target=self, get_ball=True)

        else:
            self.setup_player_controlled_eject(balls, device, trigger_event)

    def setup_player_controlled_eject(self, balls, device, trigger_event):
        """Used to set up an eject from a ball device which will eject a ball to
        the playfield.

        Args:
            balls: Integer of the number of balls this device should eject.
            device: The ball device object that will eject the ball(s) when a
                switch with the player-controlled eject tag is hit.
            trigger_event: The name of the MPF event that will trigger the
                eject.

        When this method it called, MPF will set up an event handler to look for
        the trigger_event.
        """

        if not device.balls:
            device.request_ball(balls=balls)

        self.machine.events.add_handler(trigger_event,
                                        self.player_eject_request,
                                        balls=balls, device=device)

    def remove_player_controlled_eject(self):
        """Removed the player-controlled eject so a player hitting a switch
        no longer calls the device(s) to eject a ball.
        """
        self.machine.events.remove_handler(self.player_eject_request)

    def player_eject_request(self, balls, device):
        """A player has hit a switch tagged with the player_eject_request_tag.

        Args:
            balls: Integer of the number of balls that will be ejected.
            device: The ball device object that will eject the ball(s).
        """

        self.log.debug("Received player eject request. Balls: %s, Device: %s",
                       balls, device.name)
        device.eject(balls, target=self)

    def playfield_switch_hit(self):
        """A switch tagged with 'playfield_active' was just hit, indicating that
        there is at least one ball on the playfield.
        """
        if not self.balls:

            if not self.num_balls_requested:
                self.log.debug("PF switch hit with no balls expected. Setting "
                               "pf balls to 1.")
                self.balls = 1
                self.machine.events.post('Unexpected_ball_on_playfield')

    def _ball_added_handler(self, balls):
        self.log.debug("%s ball(s) added to the playfield", balls)
        self.balls += balls

    def _ball_removed_handler(self, balls):
        self.log.debug("%s ball(s) removed from the playfield", balls)
        self.balls -= balls

    def _source_device_eject_attempt(self, balls, target, **kwargs):
        # A source device is attempting to eject a ball. We need to know if it's
        # headed to the playfield.
        if target == self:
            self.log.debug("A source device is attempting to ejected %s ball(s)"
                           " to the playfield.", balls)
            self.num_balls_requested += balls

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
                self.log.critical("num_balls_requested is %s, which doesn't "
                                  "make sense. Quitting...",
                                  self.num_balls_requested)
                raise Exception("num_balls_requested is %s, which doesn't make "
                                "sense. Quitting...", self.num_balls_requested)

            self.remove_player_controlled_eject()

    def ok_to_confirm_ball_via_playfield_switch(self):
        """Used to check whether it's ok for a ball device which ejects to the
        playfield to confirm its eject via a playfield switch being hit.

        Returns: True or False

        Right now this is simple. If there are no playfield balls, then any
        playfield switch hit is assumed to be from the newly-ejected ball. If
        there are other balls on the playfield, then we can't use this
        confirmation method since we don't know whether a playfield switch hit
        is from the newly-ejected ball(s) or a current previously-live
        playfield ball.
        """
        if not self.balls:
            return True
        else:
            return False

        # todo look for other incoming balls?

    # BALL SEARCH --------------------------------------------------------------

    # todo make ball search work with plunger lanes with no switches. i.e. we
    # don't want ball search to start until a switch is hit?

    def ball_search_schedule(self, secs=None, force=False):
        """Schedules a ball search to start. By default it will schedule it
        based on the time configured in the machine configuration files.

        If a ball search is already scheduled, this method will reset that
        schedule to the new time passed.

        Args:
            secs: Schedules the ball search that many secs from now.
            force : Boolean to force a ball search. Set True to force a ball
                search. Otherwise it will only schedule it if
                self.flag_no_ball_search is False. Default is False

        """
        if self.machine.config['ballsearch']:
            if not self.flag_no_ball_search or force is True:
                if secs is not None:
                    start_ms = secs * 1000
                else:
                    start_ms = (self.machine.config['ballsearch']
                        ['secs until ball search start'] * 1000)
                self.log.debug("Scheduling a ball search for %s secs from now",
                               start_ms / 1000.0)
                self.delay.reset("ball_search_start",
                                 ms=start_ms,
                                 callback=self.ball_search_begin)

    def ball_search_disable(self):
        """Disables ball search.

        Note this is used to prevent a future ball search from happening (like
        when all balls become contained). This method is not used to cancel an
        existing ball search. (Use `ball_search_end` for that.)

        """
        self.log.debug("Disabling Ball Search")
        self.delay.remove('ball_search_start')

    def ball_search_begin(self, force=False):
        """Begin the ball search process"""
        if not self.flag_no_ball_search:
            self.log.debug("Received request to start ball search")
            # ball search should only start if we have uncontained balls
            if self.balls or force:
                # todo add audit
                self.flag_ball_search_in_progress = True
                self.machine.events.post("ball_search_begin_phase1")
                # todo set delay to start phase 2

            else:
                self.log.debug("We got request to start ball search, but we "
                               "have no balls uncontained. WTF??")

    def ball_search_failed(self):
        """Ball Search did not find the ball."""
        self.log.debug("Ball Search failed to find a ball. Disabling.")
        self.ball_search_end()
        self.ball_lost()

    def ball_search_end(self):
        """End the ball search, either because we found the ball or
        are giving up."""
        self.log.debug("Ball search ending")
        self.flag_ball_search_in_progress = False
        self.machine.events.post("ball_search_end")
        # todo cancel the delay for phase 2 if we had one

    def ball_lost(self):
        """Mark a ball as lost"""
        self.num_balls_known = self.balls
        self.num_balls_missing = self.machine.config['machine']\
            ['balls installed'] - self.balls
        self.num_balls_live = 0
        # since desired count doesn't change, this will relaunch them
        self.log.debug("Ball(s) Marked Lost. Known: %s, Missing: %s",
                       self.num_balls_known, self.num_balls_missing)

        # todo audit balls lost

    def ball_found(self, num=1):
        """Used when a previously missing ball is found. Updates the balls
        known and balls missing variables.

        Parameters
        ----------

        num : int
            Specifies how many balls have been found. Default is 1.

        """
        self.log.debug("HEY!! We just found %s lost ball(s).", num)
        self.num_balls_known += num
        self.num_balls_missing -= num
        self.log.debug("New ball counts. Known: %s, Missing: %s",
                       self.num_balls_known, self.num_balls_missing)
        self.ball_update_all_counts()  # is this necessary? todo

    def eject(self, *args, **kwargs):
        pass

    def eject_all(self, *args, **kwargs):
        pass

# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
