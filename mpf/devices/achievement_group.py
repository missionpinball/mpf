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
        self._selected_member = None

    @property
    def enabled(self):
        """Return enabled state."""
        return self._enabled

    def enable(self, **kwargs):
        """Enable achievement group."""
        del kwargs

        if self._enabled:
            return

        self._enabled = True

        self._stop_show()

        show = self.config['show_when_enabled']

        if show:
            self._show = self.machine.shows[show].play(
                priority=self._mode.priority,
                loops=-1,
                show_tokens=self.config['show_tokens'])

        for e in self.config['events_when_enabled']:
            self.machine.events.post(e)

        self._process_current_member_state()

    def disable(self, **kwargs):
        """Disable achievement group."""
        del kwargs
        if not self._enabled:
            return
        self._stop_show()
        self._enabled = False
        self._selected_member = None

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
        if not self._selected_member:
            self.select_random_achievement()

        return self._selected_member

    def start_selected(self, **kwargs):
        """Start the currently selected achievement."""
        del kwargs
        if not self._enabled:
            return

        try:
            self._get_current().start()
        except AttributeError:
            # don't have a current one
            pass

    def rotate_right(self, reverse=False, **kwargs):
        """Rotate to the right."""
        del kwargs
        if not self._is_ok_to_change_selection():
            return

        if not self._selected_member and not self.config['auto_select']:
            return

        # if there's already one selected, set it back to enabled
        if self._selected_member and self._selected_member.state == "selected":
            self._selected_member.enable()

        achievements = self._get_available_achievements()

        try:
            current_index = achievements.index(self._get_current())
        except ValueError:
            self._selected_member = self._get_current()
        else:
            if reverse:
                self._selected_member = achievements[(current_index - 1) % len(achievements)]
            else:
                self._selected_member = achievements[(current_index + 1) % len(achievements)]

        self._selected_member.select()

    def rotate_left(self, **kwargs):
        """Rotate to the left."""
        del kwargs
        self.rotate_right(reverse=True)

    def _no_more_enabled(self):
        """Post event when no more enabled achievements are available."""
        for e in self.config['events_when_no_more_enabled']:
            self.machine.events.post(e)

    def _all_complete(self):
        self.disable()  # disable before event post so event can reenable

        for e in self.config['events_when_all_completed']:
            self.machine.events.post(e)

    def select_random_achievement(self, **kwargs):
        """Select a random achievement."""
        del kwargs

        if not self._is_ok_to_change_selection():
            return

        if self._selected_member and self._selected_member.state == "selected":
            self._selected_member.enable()

        try:
            ach = choice(self._get_available_achievements())
            # todo change this to use our Randomizer class
            self._selected_member = ach
            ach.select()
        except IndexError:
            self._no_more_enabled()

    def _is_ok_to_change_selection(self):
        if (not self._enabled and
                not self.config['allow_selection_change_while_disabled']):
            return False
        return True

    def member_state_changed(self):
        """Notify the group that one of its member achievements has changed state."""
        self._check_for_auto_start_stop()
        self._process_current_member_state()

    def _process_current_member_state(self):
        if not self._enabled:
            return

        self._check_for_all_complete()
        self._check_for_no_more_enabled()
        self._update_selected()

        if not self._selected_member and self.config['auto_select']:
            self.select_random_achievement()

    def _update_selected(self):
        for ach in self.config['achievements']:
            if ach.state == 'selected':
                self._selected_member = ach
                return True

        if self.config['auto_select']:
            self.select_random_achievement()

        return False

    def _check_for_all_complete(self):
        if not self._enabled:
            return

        if not [x for x in self.config['achievements'] if x.state != "completed"]:
            self._all_complete()
            return True
        return False

    def _check_for_no_more_enabled(self):
        if not self._enabled:
            return

        if not [x for x in self.config['achievements'] if x.state == "enabled"]:
            self._no_more_enabled()
            return True
        return False

    def _check_for_auto_start_stop(self):
        if self._is_member_started():
            if self.config['disable_while_achievement_started']:
                self.disable()

        elif self.config['enable_while_no_achievement_started']:
            self.enable()

    def _is_member_started(self):
        for ach in self.config['achievements']:
            if ach.state == 'started':
                return True

        return False

    def device_added_to_mode(self, mode: Mode, player: Player):
        """Load device on mode start and restore state.

        Args:
            mode: mode which was contains the device
            player: player which is currently active
        """
        super().device_added_to_mode(mode, player)

        self._mode = mode

        for ach in self.config['achievements']:
            ach.add_to_group(self)

        self.member_state_changed()

        if (not self._enabled and
                not self.config['enable_events'] and
                not self.config['disable_while_achievement_started']):
            self.enable()

    def device_removed_from_mode(self, mode: Mode):
        """Mode ended.

        Args:
            mode: mode which stopped
        """
        del mode
        self._mode = None

        for ach in self.config['achievements']:
            ach.remove_from_group(self)

        if self._show:
            self._show.stop()
