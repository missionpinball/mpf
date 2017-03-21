"""Device that implements an extra ball."""
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player


class ExtraBall(ModeDevice):

    """An extra ball which can be awarded once per player."""

    config_section = 'extra_balls'
    collection = 'extra_balls'
    class_label = 'extra_ball'

    def __init__(self, machine, name):
        """Initialise extra ball."""
        super().__init__(machine, name)
        self.player = None

    def award(self, **kwargs):
        """Award extra ball to player if enabled."""
        del kwargs

        if not self.player:
            return

        if (self.config['max_per_game'] and
                self.player.extra_balls_awarded[self.name] <
                self.config['max_per_game']):

            if self.machine.extra_ball_controller.enabled:
                self.player.extra_balls_awarded[self.name] += 1

            # still need to send this even if EBs are disabled since we want
            # to post the disabled event
            self.machine.extra_ball_controller.award()

    def light(self, **kwargs):
        del kwargs

        if not self.player:
            return

        self.machine.extra_ball_controller.light()

    def reset(self, **kwargs):
        """Reset extra ball.

        Does not reset the additional ball the player received. Only resets the device and allows to award another
        extra ball to the player.
        """
        del kwargs

        if not self.player:
            return

        self.player.extra_balls_awarded[self.name] = 0

    def device_added_to_mode(self, mode: Mode, player: Player):
        """Load extra ball in mode and initialise player.

        Args:
            mode: Mode which is loaded
            player: Current player
        """
        super().device_added_to_mode(mode, player)
        self.player = player

        if self.name not in self.player.extra_balls_awarded:
            self.player.extra_balls_awarded[self.name] = 0

    def device_removed_from_mode(self, mode: Mode):
        """Unload extra ball.

        Args:
            mode: Mode which is unloaded
        """
        del mode
        self.player = None
