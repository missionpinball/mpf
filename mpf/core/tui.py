"""Contains the TextUI class."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from asciimatics.screen import Screen
from psutil import cpu_percent
import mpf._version

if TYPE_CHECKING:   # pragma: no cover
    from mpf.core.machine import MachineController


class TextUi(object):
    """Handles the text-based UI"""

    def __init__(self, machine: "MachineController") -> None:
        """Initialize TextUi."""

        if not machine.options['text_ui']:
            return

        self.start_time = datetime.now()
        self.machine = machine
        self.machine.clock.schedule_interval(self._tick, 1)
        self.screen = self.machine.options['screen']

        self.machine.events.add_handler('init_phase_1', self._init)
        self.machine.events.add_handler('init_phase_3', self._update_switches)
        self.machine.events.add_handler('loading_assets',
                                        self._asset_load_change)
        self.machine.events.add_handler('bcp_connection_attempt',
                                        self._bcp_connection_attempt)
        self.machine.events.add_handler('asset_loading_complete',
                                        self._asset_load_complete)
        self.machine.events.add_handler('bcp_clients_connected',
                                        self._bcp_connected)

        self._pending_bcp_connection = False
        self._asset_percent = 0

        self._draw_screen()

    def _init(self, **kwargs):
        del kwargs
        self.machine.mode_controller.register_start_method(self._mode_change)
        self.machine.mode_controller.register_stop_method(self._mode_change)
        self.machine.switch_controller.add_monitor(self._update_switches)

    def _draw_screen(self):
        title = 'Mission Pinball Framework v{}'.format(
            mpf._version.__version__)
        padding = int((self.screen.width - len(title)) / 2)

        self.screen.print_at((' ' * padding) + title + (' ' * (padding + 1)),
                             0, 0, colour=7, bg=1)

        self.screen.print_at('ACTIVE MODES', 1, 1)
        self.screen.print_at('ACTIVE SWITCHES', int(self.screen.width / 2), 1)
        self.screen.print_at('-' * self.screen.width, 0, 2)

        self.screen.print_at(self.machine.machine_path,
                             0, self.screen.height-1,
                             colour=3)

        if 0 < self._asset_percent < 100:
            self.screen.print_at(
                'LOADING ASSETS: {}%'.format(self._asset_percent),
                int(self.screen.width / 2) - 10, int(self.screen.height / 2) + 1,
                colour=0, bg=3)

        if self._pending_bcp_connection:
            bcp_string = 'WAITING FOR MEDIA CONTROLLER {}...'.format(
                self._pending_bcp_connection)

            self.screen.print_at(
                bcp_string,
                int((self.screen.width - len(bcp_string)) / 2),
                int(self.screen.height / 2) - 1,
                colour=0, bg=3)

        self._update_runtime()

    def _update_runtime(self):
        rt = (datetime.now() - self.start_time)

        min, sec = divmod(rt.seconds + rt.days * 86400, 60)
        hours, min = divmod(min, 60)

        time_string = 'RUNNING {:d}:{:02d}:{:02d}'.format(hours, min, sec)
        self.screen.print_at(time_string, self.screen.width - len(time_string),
                             self.screen.height-1, colour=2, bg=0)

        cpu_string = 'CPU:{:3d}%'.format(round(cpu_percent(interval=None,
                                                           percpu=False)))

        self.screen.print_at(
            cpu_string,
            self.screen.width - len(time_string) - len(cpu_string) - 3,
            self.screen.height-1, colour=6, bg=0)

        self.screen.refresh()

    def _update_switches(self, *args, **kwargs):
        del args
        del kwargs
        switches = sorted(list(
            x.name for x in self.machine.switches if x.state))

        for i, switch in enumerate(switches):
            self.screen.print_at(' ' * int(self.screen.width / 2),
                                 int(self.screen.width / 2), i+3)
            self.screen.print_at(switch, int(self.screen.width / 2), i+3)

        self.screen.print_at(' ' * int(self.screen.width / 2),
                             int(self.screen.width / 2), len(switches)+3)
        self.screen.refresh()

    def _mode_change(self, *args, **kwargs):
        # Have to call this on the next frame since the mode controller's
        # active list isn't updated yet
        del args
        del kwargs
        self.machine.clock.schedule_once(self._update_modes)

    def _update_modes(self, *args, **kwargs):
        del args
        del kwargs
        modes = self.machine.mode_controller.active_modes

        for i, mode in enumerate(modes):
            self.screen.print_at(' ' * (int(self.screen.width / 2) - 1),
                                 1, i+3)
            self.screen.print_at(mode.name, 1, i+3)

        self.screen.print_at(' ' * (int(self.screen.width / 2) - 1),
                             1, len(modes) + 3)
        self.screen.refresh()

    def _tick(self):
        if self.screen.has_resized():
            self.screen = Screen.open()
            self._draw_screen()
            self._update_switches()
            self._update_modes()

        else:
            self._update_runtime()

    def _bcp_connection_attempt(self, name, host, port, **kwargs):
        del name
        del kwargs
        self._pending_bcp_connection = '{}:{}'.format(host, port)
        self._draw_screen()

    def _bcp_connected(self, **kwargs):
        del kwargs
        self._pending_bcp_connection = None
        self.screen.print_at(' ' * self.screen.width,
                             0, int(self.screen.height / 2) - 1)

    def _asset_load_change(self, percent, **kwargs):
        del kwargs
        self._show_asset_loading(percent)

    def _show_asset_loading(self, percent=None):
        if percent is None:
            percent = self._asset_percent
        else:
            self._asset_percent = percent

        self._draw_screen()

    def _asset_load_complete(self, **kwargs):
        del kwargs
        self._asset_percent = 100
        self.screen.print_at(' ' * self.screen.width,
                             0, int(self.screen.height / 2) + 1)
