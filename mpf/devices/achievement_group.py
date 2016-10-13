"""An achievement group which manages and groups achievements."""
from collections import deque

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
        self._complete_achievements = set()

    def enable(self, **kwargs):
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

    def disable(self, **kwargs):
        self._stop_show()
        self._enabled = False

    def _stop_show(self):
        if self._show:
            self._show.stop()
            self._show = None

    def start_selected(self, **kwargs):
        if not self._enabled:
            return

        for ach in [x for x in self.config['achievements'] if
                    x.state == 'selected']:
            ach.start()

    def rotate_right(self, reverse=False, **kwargs):
        achievements = ([x for x in self.config['achievements'] if
            x.state in ('enabled', 'selected')])

        for index, a in enumerate(achievements):
            if a.state == 'selected':
                a.enable()

                if not reverse:
                    try:
                        achievements[index+1].select()
                    except IndexError:
                        achievements[0].select()
                else:
                    achievements[index-1].select()

                return

    def rotate_left(self, **kwargs):
        self.rotate_right(reverse=True)

    def no_more_enabled(self):
        for e in self.config['events_when_no_more_enabled']:
            self.machine.events.post(e)

    def all_complete(self):
        for e in self.config['events_when_all_complete']:
            self.machine.events.post(e)

    def select_random_achievement(self, **kwargs):
        try:
            ach = choice([x for x in self.config['achievements'] if
                 x.state == 'enabled' or
                 (x.state == 'stopped' and
                  x.config['restart_after_stop_possible'])])
            ach.select()

        except IndexError:
            self.no_more_enabled()

    def _member_state_changed(self, achievement, **kwargs):
        del kwargs

        state = achievement.state

        if state == 'completed':
            self._complete_achievements.add(achievement)
        else:
            self._complete_achievements.discard(achievement)

        self._check_for_all_complete()

    def _check_for_all_complete(self):
        if len(self._complete_achievements) == len(
                self.config['achievements']):
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
