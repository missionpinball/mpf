"""An achievement group which manages and groups achievements."""
from typing import Optional, List

from random import choice

from mpf.core.events import event_handler, EventHandlerKey
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.device_monitor import DeviceMonitor

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.achievement import Achievement     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.assets.show import RunningShow     # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor(_enabled="enabled", _selected_member="selected_member")
class AchievementGroup(ModeDevice):

    """An achievement group in a pinball machine.

    It is tracked per player and can automatically restore state on the next
    ball.
    """

    __slots__ = ["_show", "_enabled", "_selected_member", "_rotation_in_progress", "_handlers", "_loaded"]

    config_section = 'achievement_groups'
    collection = 'achievement_groups'
    class_label = 'achievement_group'

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize achievement."""
        super().__init__(machine, name)

        self._show = None       # type: Optional[RunningShow]

        self._enabled = False
        self._loaded = False
        self._selected_member = None    # type: Optional[Achievement]
        self._rotation_in_progress = False
        self._handlers = []             # type: List[EventHandlerKey]

    @property
    def enabled(self):
        """Return enabled state."""
        return self._enabled

    def enable(self):
        """Enable achievement group."""
        if not self._loaded:
            return

        if self._enabled:
            self.debug_log("Group is already enabled. Aborting")
            return

        if self._is_member_started() and self.config['disable_while_achievement_started']:
            self.debug_log("Not enabling because a member is started and disable_while_achievement_started is true.")
            return

        super().enable()
        self.debug_log("Call to enable this group")

        self._enabled = True
        self.debug_log("Enabling group")

        self._stop_show()
        if self._selected_member and self._selected_member.selected:
            self._selected_member = None

        show = self.config['show_when_enabled']

        if show:
            self._show = show.play(
                priority=self.mode.priority,
                loops=-1, sync_ms=self.config['sync_ms'],
                show_tokens=self.config['show_tokens'])

        for e in self.config['events_when_enabled']:
            self.machine.events.post(e)

        self._process_current_member_state()

    @event_handler(0)
    def event_disable(self, **kwargs):
        """Event handler for disable event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable achievement group."""
        if not self._enabled:
            self.debug_log("Group is already disabled. Aborting")
            return
        self.debug_log("Disabling group")
        self._stop_show()
        self._enabled = False

    def _stop_show(self):
        if self._show:
            self.debug_log("Stopping show")
            self._show.stop()
            self._show = None

    def _get_available_achievements_for_selection(self):
        """Return achievements which can be selected and started."""
        return [x for x in self.config['achievements'] if x.can_be_selected_for_start]

    def _get_current(self):
        self.debug_log("Getting current selected achievement")
        if not self._selected_member:
            self.select_random_achievement()

        return self._selected_member

    @event_handler(5)
    def event_start_selected(self, **kwargs):
        """Event handler for start_selected event."""
        del kwargs
        self.start_selected()

    def start_selected(self):
        """Start the currently selected achievement."""
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
    def event_rotate_right(self, reverse=False, **kwargs):
        """Event handler for rotate_right event."""
        del kwargs
        self.rotate_right(reverse)

    def rotate_right(self, reverse=False):
        """Rotate to the right."""
        self.debug_log("Call to rotate")
        if not self._is_ok_to_change_selection():
            return

        if not self._selected_member and not self.config['auto_select']:
            self.debug_log("Nothing selected and auto_select false. Abort.")
            return

        self._rotation_in_progress = True

        # if there's already one selected, set it back to enabled
        if self._selected_member and self._selected_member.selected:
            self._selected_member.unselect()

        achievements = self._get_available_achievements_for_selection()
        if not achievements:
            # there is nothing to rotate
            self.debug_log("Nothing to rotate. Abort.")
            return

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
    def event_rotate_left(self, **kwargs):
        """Event handler for rotate_left event."""
        del kwargs
        self.rotate_left()

    def rotate_left(self):
        """Rotate to the left."""
        self.rotate_right(reverse=True)

    def _no_more_enabled(self):
        """Post event when no more enabled achievements are available."""
        self.debug_log("No more achievements are enabled")
        for e in self.config['events_when_no_more_enabled']:
            self.machine.events.post(e)

    def _all_complete(self):
        self.debug_log("All achievements are complete")
        self.disable()  # disable before event post so event can re-enable

        for e in self.config['events_when_all_completed']:
            self.machine.events.post(e)

    @event_handler(9)
    def event_select_random_achievement(self, **kwargs):
        """Event handler for select_random_achievement event."""
        del kwargs
        if self.config['disable_random']:
            self.rotate_right()
        else:
            self.select_random_achievement()

    def select_random_achievement(self):
        """Select a random or sequential achievement."""
        self.debug_log("Selecting an achievement")

        if not self._is_ok_to_change_selection():
            self.debug_log("Not ok to change selection. Aborting")
            return

        if self._selected_member and self._selected_member.selected:
            self._selected_member.unselect()

        try:
            # todo change this to use our Randomizer class
            if self.config['disable_random']:
                ach = self._get_available_achievements_for_selection()[0]
                self.debug_log("Picked new non-random achievement: %s", ach)
            else:
                ach = choice(self._get_available_achievements_for_selection())
                self.debug_log("Picked new random achievement: %s", ach)
            self._selected_member = ach
            ach.select()
        except IndexError:
            self._no_more_enabled()

    def _is_ok_to_change_selection(self):
        self.debug_log("Checking if it's ok to change selection...")
        if self._enabled:
            self.debug_log("Ok because enabled")
            return True
        if self.config['allow_selection_change_while_disabled']:
            self.debug_log("Ok because allow_selection_change_while_disabled is set (but disabled)")
            return True

        self.debug_log("not ok")
        return False

    def member_state_changed(self, **kwargs):
        """Notify the group that one of its members has changed state."""
        del kwargs
        if not self._loaded:
            return
        self.debug_log("Member state has changed")
        if self._is_member_started():
            self.debug_log("A member is started")
            if self.config['disable_while_achievement_started'] and self.enabled:
                self.debug_log("disable_while_achievement_started is true")
                self.disable()
            else:
                self._process_current_member_state()

        elif self.config['enable_while_no_achievement_started'] and not self.enabled:
            self.debug_log("enable_while_no_achievement_started is true")
            self.enable()
        else:
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
        if self._check_for_no_more_enabled():
            self.debug_log("No achievement enabled. Aborting.")
            return
        self._update_selected()

        if not self._selected_member and self.config['auto_select']:
            self.debug_log("No selected member, but auto_select is true")
            self.select_random_achievement()

    def _update_selected(self):
        self.debug_log("Updating selected achievement")
        for ach in self.config['achievements']:
            if ach.selected:
                self._selected_member = ach
                self.debug_log("Already have a selected member is %s", ach)
                return True

            self.debug_log("Do not have a current selected member")

        if self.config['auto_select']:
            self.debug_log("Auto select is true. Getting achievement")
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

        if not self._get_available_achievements_for_selection():
            self._no_more_enabled()
            return True
        return False

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
        ----
            mode: mode which was contains the device
            player: player which is currently active
        """
        super().device_loaded_in_mode(mode, player)
        self._loaded = True

        for ach in self.config['achievements']:
            self._handlers.append(self.machine.events.add_handler("achievement_{}_changed_state".format(ach.name),
                                                                  self.member_state_changed))

        if self.config['enable_while_no_achievement_started'] and self._is_member_started() and not self._enabled:
            self.enable()

    def device_removed_from_mode(self, mode: Mode):
        """Mode ended.

        Args:
        ----
            mode: mode which stopped
        """
        super().device_removed_from_mode(mode)

        self.machine.events.remove_handlers_by_keys(self._handlers)
        self._handlers = []

        self.disable()
        self._loaded = False
        self._selected_member = None

        if self._show:
            self._show.stop()

    def _enable_related_device_debugging(self):
        for ach in self.config['achievements']:
            ach.enable_debugging()
