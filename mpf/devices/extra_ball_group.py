"""Device that implements an extra ball group."""
from typing import Optional

from mpf.core.events import event_handler
from mpf.core.machine import MachineController
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.player import Player


@DeviceMonitor("enabled")
class ExtraBallGroup(SystemWideDevice):

    """Tracks and manages groups of extra balls devices."""

    config_section = 'extra_ball_groups'
    collection = 'extra_ball_groups'
    class_label = 'extra_ball_group'

    __slots__ = ["player", "_player_var_per_game", "_player_var_per_ball", "_player_var_num_lit"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize ExtraBallGroup."""
        super().__init__(machine, name)

        self.player = None  # type: Optional[Player]
        self.machine.events.add_handler('player_added',
                                        self._player_added)
        self.machine.events.add_handler('player_turn_starting',
                                        self._player_turn_starting)
        self.machine.events.add_handler('player_turn_ending',
                                        self._player_turn_ending)
        self.machine.events.add_handler('ball_started',
                                        self._ball_started)

        self._player_var_per_game = 'extra_ball_group_{}_num_awarded_game'.format(name)
        self._player_var_per_ball = 'extra_ball_group_{}_num_awarded_ball'.format(name)
        self._player_var_num_lit = 'extra_ball_group_{}_num_lit'.format(name)

    @property
    def enabled(self):
        """Return whether this extra ball group is enabled.

        This attribute considers the enabled setting plus the
        max balls per game and ball settings.
        """
        if not self.player or not self.config['enabled']:
            return False

        if (self.config['max_per_game'] and self.config['max_per_game'] <=
                self.player[self._player_var_per_game]):
            return False

        if (self.config['max_per_ball'] and self.config['max_per_ball'] <=
                self.player[self._player_var_per_ball]):
            return False

        return True

    def _player_added(self, player, **kwargs):
        # called once per player to setup their vars for this group
        del kwargs

        player[self._player_var_per_game] = 0
        player[self._player_var_num_lit] = 0
        player[self._player_var_per_ball] = 0

    def _player_turn_starting(self, player, number, **kwargs):
        # reset the num of EBs awarded per ball. We do this on turn start
        # rather than ball start because a player shooting again is technically
        # another ball start even though it's the same ball number
        del number, kwargs

        self.player = player
        player[self._player_var_per_ball] = 0

    def _ball_started(self, ball, player, **kwargs):
        # check if we need to relight the group
        del ball, player, kwargs
        if self.player[self._player_var_num_lit]:
            self._post_lit_events()

    def _player_turn_ending(self, player, number, **kwargs):
        # clear the lit if lit memory is disabled
        del number, kwargs

        if not self.config['lit_memory']:
            player[self._player_var_num_lit] = 0

        self.player = None

    def is_ok_to_light(self) -> bool:
        """Check if it's possible to light an extra ball.

        Returns True or False.

        This method checks to see if the group is enabled and whether the
        max_lit setting has been exceeded.
        """
        if not self.enabled or not self.player:
            return False

        return not (
            self.config['max_lit'] and self.config['max_lit'] <=
            self.player[self._player_var_num_lit])

    @event_handler(2)
    def event_award_lit(self, **kwargs):
        """Handle award_lit control event."""
        del kwargs
        self.award_lit()

    def award_lit(self):
        """Award a lit extra ball.

        If the player does not have any lit extra balls, this method does
        nothing.
        """
        if not self.player:
            return

        if not self.enabled:
            self.award_disabled()
            return

        if self.player[self._player_var_num_lit] < 1:
            return

        self.player[self._player_var_num_lit] -= 1

        if not self.player[self._player_var_num_lit]:
            self._post_unlit_events()
            posted_unlit_events = True
        else:
            posted_unlit_events = True

        self.award(posted_unlit_events=posted_unlit_events)

    @event_handler(1)
    def event_award(self, posted_unlit_events=False, **kwargs):
        """Handle award control event."""
        del kwargs
        self.award(posted_unlit_events)

    def award(self, posted_unlit_events=False):
        """Immediately awards an extra ball.

        This event first checks to make sure the limits of the max extra
        balls have not been exceeded and that this group is enabled.

        Note that this method will work even if this group does not have any
        extra balls or extra balls lit. You can use this to directly award an
        extra ball.
        """
        if not self.enabled:
            self.award_disabled()
            return

        self.machine.events.post('extra_ball_group_{}_awarded'.format(self.name))
        '''event: extra_ball_group_(name)_awarded

        desc: An extra ball from this group was just awarded. This is a
        good event to use to trigger award shows, sounds, etc.
        '''
        self.player[self._player_var_per_game] += 1
        self.player[self._player_var_per_ball] += 1
        self.player.extra_balls += 1
        self.machine.events.post('extra_ball_awarded')

        # if this award puts us over the max limits, make sure none are lit
        if not self.enabled:
            self.player['extra_ball_group_{}_num_lit'] = 0
            if not posted_unlit_events:
                self._post_unlit_events()

    @event_handler(3)
    def event_light(self, **kwargs):
        """Handle light control event."""
        del kwargs
        self.light()

    def light(self):
        """Light the extra ball for possible collection by the player.

        This method checks that the group is enabled and that the max lit
        value has not been exceeded. If so, this method will post the extra
        ball disabled events.
        """
        if self.is_ok_to_light():
            self.player[self._player_var_num_lit] += 1

            self.machine.events.post(
                'extra_ball_group_{}_lit_awarded'.format(self.name))
            '''event: extra_ball_group_(name)_lit_awarded

            desc: This even is posted when an extra ball is lit during play.
            It is NOT posted when a player's turn starts if they have a lit
            extra ball from their previous turn. Therefore this event is a
            good event to use for your award slides and shows when a player
            lights the extra ball, because you don't want to use
            :doc:`extra_ball_group_extra_ball_group_lit` because that is also posted when
            the player's turn starts and you don't want the award show to play
            again when they're starting their turn.
            '''

            self._post_lit_events()

        else:
            self._extra_ball_award_disabled()

    def _post_lit_events(self, **kwargs):
        del kwargs

        self.machine.events.post(
            'extra_ball_group_{}_lit'.format(self.name))
        '''event: extra_ball_group_(name)_lit

        desc: An extra ball was just lit. This is a good event to use to
        start your extra ball lit mode, to turn on an extra ball light,
        to play the "get that extra ball" sound, etc.

        Note that this event is posted if an extra ball is lit during play
        and also when a player's turn starts if they have a lit extra ball.

        See also the :doc:`extra_ball_extra_ball_lit` for a similar event that
        is only posted when an extra ball is lit during play, and not
        if the player starts their turn with the extra ball lit.
        '''

    def _post_unlit_events(self, **kwargs):
        del kwargs

        self.machine.events.post(
            'extra_ball_group_{}_unlit'.format(self.name))

        '''event: extra_ball_group_(name)_unlit

        desc: No more lit extra balls are available for this extra ball group.
        This is a good event to
        use as a stop event for your extra ball lit mode or whatever you're
        using to indicate to the player that an extra ball is available.
        '''

    def award_disabled(self):
        """Post the events when an extra ball connect be awarded."""
        self.machine.events.post('extra_ball_group_{}_award_disabled'.format(self.name))
        '''event: extra_ball_group_(name)_award_disabled

        desc: Posted when you have the global extra ball settings set to not
        enable extra balls but where an extra ball would have been awarded.
        This is a good alternative event to use to score points or whatever
        else you want to give the player when extra balls are disabled.

        '''
