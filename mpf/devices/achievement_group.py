"""An achievement group which manages and groups achievements."""
from random import choice

from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player


class AchievementGroup(ModeDevice):

    """An achievement group in a pinball machine.

    It is tracked per player and can automatically restore state on the next
    ball.
    """

    config_section = 'achievement_groups'
    collection = 'achievement_groups'
    class_label = 'achievement_group'

    def __init__(self, machine, name):
        """Initialize achievement."""
        super().__init__(machine, name)

        self._mode = None
        self._show = None

        self._enabled = False
        self._selected = None

    def enable(self, **kwargs):
        """Enable achievement group."""
        del kwargs
        if self._enabled and self._selected and self._show:
            # todo hack - how does it get here with no selecter and/or no show?
            return

        self._enabled = True

        show = self.config['show_when_enabled']

        self._stop_show()

        if show:
            self._show = self.machine.shows[show].play(
                priority=self._mode.priority,
                loops=-1,
                show_tokens=self.config['show_tokens'])

        for e in self.config['events_when_enabled']:
            self.machine.events.post(e)

        self._selected = None
        self._get_current().select()

    def disable(self, **kwargs):
        """Disable achievement group."""
        del kwargs
        if not self._enabled:
            return
        self._stop_show()
        self._enabled = False
        self._selected = None

    def _stop_show(self):
        if self._show:
            self._show.stop()
            self._show = None

    def _get_available_achievements(self):
        return [x for x in self.config['achievements'] if
                x.state == 'enabled' or
                x.state == 'selected' or
                (x.state == 'stopped' and
                x.config['restart_after_stop_possible'])]

    def _get_current(self):
        if not self._selected:
            self._selected = choice(self._get_available_achievements())

        return self._selected

    def start_selected(self, **kwargs):
        """Start the currently selected achievement."""
        del kwargs
        if not self._enabled:
            return
        self._get_current().start()
        self.disable()

    def rotate_right(self, reverse=False, **kwargs):
        """Rotate to the right."""
        del kwargs
        if not self._enabled:
            return
        if self._selected and self._selected.state == "selected":
            self._selected.enable()
        achievements = self._get_available_achievements()
        try:
            current_index = achievements.index(self._get_current())
        except ValueError:
            self._selected = self._get_current()
        else:
            if reverse:
                self._selected = achievements[(current_index - 1) % len(achievements)]
            else:
                self._selected = achievements[(current_index + 1) % len(achievements)]
        self._selected.select()

    def rotate_left(self, **kwargs):
        """Rotate to the left."""
        del kwargs
        self.rotate_right(reverse=True)

    def no_more_enabled(self):
        """Post event when no more enabled achievements are available."""
        for e in self.config['events_when_no_more_enabled']:
            self.machine.events.post(e)

    def all_complete(self):
        """Poste event when all achievements have been completed."""
        for e in self.config['events_when_all_complete']:
            self.machine.events.post(e)
        self.disable()

    def select_random_achievement(self, **kwargs):
        """Select a random achievement."""
        del kwargs
        # TODO: do we need this?
        if not self._enabled:
            return

        if self._selected and self._selected.state == "selected":
            self._selected.enable()
        try:
            ach = choice(self._get_available_achievements())
            # todo change this to use our Randomizer class
            self._selected = ach
            ach.select()

        except IndexError:
            self.no_more_enabled()

    def _member_state_changed(self, achievement, **kwargs):
        del kwargs
        del achievement

        self._check_for_all_complete()

        if self._enabled and self._selected and self._selected.state != "selected":
            self._selected = None
            self._get_current().select()

    def _check_for_all_complete(self):
        if not [x for x in self.config['achievements'] if x.state != "complete"]:
            self.all_complete()

    def device_added_to_mode(self, mode: Mode, player: Player):
        """Load device on mode start and restore state.

        Args:
            mode: mode which was contains the device
            player: player which is currently active
        """
        super().device_added_to_mode(mode, player)

        self._mode = mode

        states = ['disabled', 'enabled', 'started', 'stopped', 'selected',
                  'completed']

        for ach in self.config['achievements']:

            for state in states:
                mode.add_mode_event_handler(
                    ach.config['events_when_{}'.format(state)][0],
                    self._member_state_changed,
                    achievement=ach)

    def device_removed_from_mode(self, mode: Mode):
        """Mode ended.

        Args:
            mode: mode which stopped
        """
        del mode
        self._mode = None
        if self._show:
            self._show.stop()
