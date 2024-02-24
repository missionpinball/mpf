"""Device that implements an extra ball."""
from typing import Optional

from mpf.core.events import event_handler
from mpf.core.machine import MachineController
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.devices.extra_ball_group import ExtraBallGroup


@DeviceMonitor("enabled")
class ExtraBall(ModeDevice):

    """An extra ball which can be awarded once per player."""

    config_section = 'extra_balls'
    collection = 'extra_balls'
    class_label = 'extra_ball'

    __slots__ = ["player", "group", "_player_var_name"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """initialize extra ball."""
        super().__init__(machine, name)
        self.player = None  # type: Optional[Player]
        """The current player"""
        self.group = None   # type: Optional[ExtraBallGroup]
        """The ExtraBallGroup this ExtraBall belongs to, or None."""
        self._player_var_name = 'extra_ball_{}_num_awarded'.format(name)

    @property
    def enabled(self):
        """Return whether this extra ball group is enabled.

        This takes into consideration the enabled setting plus the max balls
        per game setting.
        """
        return self.is_ok_to_award()

    async def _initialize(self):
        await super()._initialize()
        self.group = self.config['group']

    @event_handler(2)
    def event_light(self, **kwargs):
        """Handle light control event."""
        del kwargs
        self.light()

    def light(self):
        """Light an extra ball for potential collection by the player.

        Lighting an extra ball will immediately increase count against the
        ``max_per_game`` setting, even if the extra ball is a member of a
        group that's disabled or if the player never actually collects the
        extra ball.

        Note that this only really does anything if this extra ball is a
        member of a group.
        """
        if self.is_ok_to_light():
            self.machine.events.post('extra_ball_{}_lit'.format(self.name))
            '''event: extra_ball_(name)_lit
            desc: The extra ball called (name) has just been lit.
            '''

            if self.group:
                self.group.light()
        else:
            self._award_disabled()

    @event_handler(1)
    def event_award(self, **kwargs):
        """Handle award control event."""
        del kwargs
        self.award()

    def award(self):
        """Award extra ball to player (if enabled)."""
        if self.is_ok_to_award():
            self.player[self._player_var_name] += 1
            self.machine.events.post('extra_ball_{}_awarded'.format(self.name))
            '''event: extra_ball_(name)_awarded
            desc: The extra ball called (name) has just been awarded.
            '''

            try:
                self.group.award()
            except AttributeError:
                # If this EB is in a group, the group will handle this stuff
                self.player.extra_balls += 1
                self.machine.events.post('extra_ball_awarded')
                '''event: extra_ball_awarded
                desc: An extra ball has just been awarded.
                '''

        else:  # EB cannot be awarded
            self._award_disabled()

    def is_ok_to_light(self) -> bool:
        """Check whether this extra ball can be lit.

        This method takes into consideration whether this extra ball is
        enabled, and, if this extra ball is a member of a group, whether the
        group is enabled and will allow an additional extra ball to lit.

        Returns True or False.
        """
        if self.is_ok_to_award():
            if self.group:
                if self.group.is_ok_to_light():
                    return True
            else:
                return True

        return False

    def is_ok_to_award(self) -> bool:
        """Check whether this extra ball can be awarded.

        This method takes into consideration whether this extra ball is
        enabled, whether the ``max_per_game`` has been exceeded, and, if this
        extra ball is a member of a group, whether the group is enabled and
        will allow an additional extra ball to be awarded.

        Returns True or False.
        """
        if not self.config['enabled'] or not self.player:
            return False

        if self.group and not self.group.enabled:
            return False

        if self.config['max_per_game'] and (
                self.config['max_per_game'] <=
                self.player[self._player_var_name]):
            return False

        return True

    def _award_disabled(self):
        self.machine.events.post('extra_ball_award_disabled')
        '''event: extra_ball_award_disabled
        desc: The award for an extra ball has just been disabled.
        '''

        self.machine.events.post(
            'extra_ball_{}_award_disabled'.format(self.name))
        '''event: extra_ball_(name)_award_disabled
        desc: The award for the extra ball called (name) has just been disabled.
        '''

        if self.group:
            # still need to send this even if EBs are disabled since we
            # want to post the group disabled event
            self.group.award_disabled()

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Load extra ball in mode and initialize player.

        Args:
        ----
            mode: Mode which is loaded
            player: Current player
        """
        del mode
        self.player = player

        if not player.is_player_var(self._player_var_name):
            player[self._player_var_name] = 0
        '''player_var: extra_ball_(name)_awarded

        desc: The number of times this extra ball has been awarded to the
        player in this game. Note that the default max is one (meaning that
        each extra ball can be awarded once per game), so this value will only
        be 0 or 1 unless you change the max setting for this extra ball.'''

    def device_removed_from_mode(self, mode: Mode):
        """Unload extra ball.

        Args:
        ----
            mode: Mode which is unloaded
        """
        del mode
        self.player = None
