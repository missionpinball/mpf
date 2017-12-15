"""An achievement group which manages and groups achievements."""
from random import choice

from mpf.core.events import event_handler
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.device_monitor import DeviceMonitor

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.achievement import Achievement
    from mpf.assets.show import RunningShow


@DeviceMonitor(_enabled="enabled", _selected_member="selected_member")
class AchievementGroup(ModeDevice):

    """An achievement group in a pinball machine.

    It is tracked per player and can automatically restore state on the next
    ball.
    """

    config_section = 'achievement_groups'
    collection = 'achievement_groups'
    class_label = 'achievement_group'

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize achievement."""
        super().__init__(machine, name)

        self._mode = None       # type: Mode
        self._show = None       # type: RunningShow

        self._enabled = False
        self._selected_member = None    # type: Achievement
        self._rotation_in_progress = False

    @property
    def enabled(self):
        """Return enabled state."""
        return self._enabled

    @event_handler(10)
    def enable(self, **kwargs):
        """Enable achievement group."""
        del kwargs

        self.debug_log("Call to enable this group")

        if self._enabled:
            self.debug_log("Group is already enabled. Aborting")
            return

        self._enabled = True
        self.debug_log("Enabling group")

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

    @event_handler(0)
    def disable(self, **kwargs):
        """Disable achievement group."""
        del kwargs
        self.debug_log("Call to disable this group")
        if not self._enabled:
            self.debug_log("Group is already disabled. Aborting")
            return
        self.debug_log("Disabling group")
        self._stop_show()
        self._enabled = False
        self._selected_member = None

    def _stop_show(self):
        if self._show:
            self.debug_log("Stopping show")
            self._show.stop()
            self._show = None

    def _get_available_achievements(self):

        available = [x for x in self.config['achievements'] if
                     x.state == 'enabled' or
                     x.state == 'selected' or
                     (x.state == 'stopped' and
                     x.config['restart_after_stop_possible'])]

        self.debug_log("Getting available achievements: %s", available)

        return available

    def _get_current(self):
        self.debug_log("Getting current selected achievement")
        if not self._selected_member:
            self.select_random_achievement()

        return self._selected_member

    @event_handler(5)
    def start_selected(self, **kwargs):
        """Start the currently selected achievement."""
        del kwargs
        self.debug_log("Call to start selected achievement")
        if not self._enabled:
            self.debug_log("Group not enabled. Aborting")
            return

        try:
            self._get_current().start()
        except AttributeError:
            # don't have a current one
            pass

    @event_handler(6)
    def rotate_right(self, reverse=False, **kwargs):
        """Rotate to the right."""
        del kwargs
        self.debug_log("Call to rotate")
        if not self._is_ok_to_change_selection():
            return

        if not self._selected_member and not self.config['auto_select']:
            return

        self._rotation_in_progress = True

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

        self._rotation_in_progress = False

    @event_handler(7)
    def rotate_left(self, **kwargs):
        """Rotate to the left."""
        del kwargs
        self.rotate_right(reverse=True)

    def _no_more_enabled(self):
        """Post event when no more enabled achievements are available."""
        self.debug_log("No more achievements are enabled")
        for e in self.config['events_when_no_more_enabled']:
            self.machine.events.post(e)

    def _all_complete(self):
        self.debug_log("All achievements are complete")
        self.disable()  # disable before event post so event can reenable

        for e in self.config['events_when_all_completed']:
            self.machine.events.post(e)

    @event_handler(9)
    def select_random_achievement(self, **kwargs):
        """Select a random achievement."""
        del kwargs

        self.debug_log("Selecting random achievement")

        if not self._is_ok_to_change_selection():
            self.debug_log("Not ok to change selection. Aborting")
            return

        if self._selected_member and self._selected_member.state == "selected":
            self.debug_log("Enabling selected member")
            self._selected_member.enable()

        try:
            ach = choice(self._get_available_achievements())
            # todo change this to use our Randomizer class
            self._selected_member = ach
            self.debug_log("Picked new random achievement: %s", ach)
            ach.select()
        except IndexError:
            self._no_more_enabled()

    def _is_ok_to_change_selection(self):
        self.debug_log("Checking if it's ok to change selection...")
        if (not self._enabled and
                not self.config['allow_selection_change_while_disabled']):
            self.debug_log("Not ok")
            return False
        self.debug_log("ok")
        return True

    def member_state_changed(self):
        """Notify the group that one of its members has changed state."""
        self.debug_log("Member state has changed")
        self._check_for_auto_start_stop()
        self._process_current_member_state()

    def _process_current_member_state(self):
        self.debug_log("Processing current member state")

        if self._rotation_in_progress:
            self.debug_log("Rotation in progress. Aborting")
            return

        if not self._enabled:
            self.debug_log("Not enabled. Aborting")
            return

        self._check_for_all_complete()
        self._check_for_no_more_enabled()
        self._update_selected()

        if not self._selected_member and self.config['auto_select']:
            self.debug_log("No selected member, but auto_select is true")
            self.select_random_achievement()

    def _update_selected(self):
        self.debug_log("Updating selected achievement")
        for ach in self.config['achievements']:
            if ach.state == 'selected':
                self._selected_member = ach
                self.debug_log("Already have a selected member is %s", ach)
                return True
            else:
                self.debug_log("Do not have a current selected member")

        if self.config['auto_select']:
            self.debug_log("Auto select is true. Getting random achievement")
            self.select_random_achievement()

        return False

    def _check_for_all_complete(self):
        self.debug_log("Checking for all complete")
        if not self._enabled:
            self.debug_log("Group is not enabled. Aborting...")
            return False

        if not [x for x in self.config['achievements'] if x.state != "completed"]:
            self._all_complete()
            return True
        self.debug_log("All are not complete")
        return False

    def _check_for_no_more_enabled(self):
        self.debug_log("Checking for no more enabled")
        if not self._enabled:
            self.debug_log("Group is disabled. Aborting...")
            return False

        if not [x for x in self.config['achievements'] if x.state == "enabled"]:
            self._no_more_enabled()
            return True
        return False

    def _check_for_auto_start_stop(self):
        self.debug_log("Checking for auto start/stop")

        if self._is_member_started():
            self.debug_log("A member is started")
            if self.config['disable_while_achievement_started']:
                self.debug_log("disable_while_achievement_started is true")
                self.disable()

        elif self.config['enable_while_no_achievement_started']:
            self.debug_log("enable_while_no_achievement_started is true")
            self.enable()

    def _is_member_started(self):
        self.debug_log("Checking if member is started")
        for ach in self.config['achievements']:
            if ach.state == 'started':
                self.debug_log("Found %s is started", ach)
                return True
        self.debug_log("No member is started")
        return False

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Load device on mode start and restore state.

        Args:
            mode: mode which was contains the device
            player: player which is currently active
        """
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

    def _enable_related_device_debugging(self):
        for ach in self.config['achievements']:
            ach.enable_debugging()
