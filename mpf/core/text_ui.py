"""Contains the TextUI class."""
import asyncio
from collections import OrderedDict
from datetime import datetime
import logging
from typing import Tuple

from asciimatics.screen import Screen
from psutil import cpu_percent, virtual_memory, Process

import mpf._version
from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController
    from mpf.devices.switch import Switch
    from typing import Dict, List
    from mpf.devices.ball_device.ball_device import BallDevice


# pylint: disable-msg=too-many-instance-attributes
class TextUi(MpfController):

    """Handles the text-based UI."""

    config_name = "text_ui"

    def __init__(self, machine: "MachineController") -> None:
        """Initialize TextUi."""
        super().__init__(machine)

        self.screen = None

        if not machine.options['text_ui']:
            return

        self.start_time = datetime.now()
        self.machine = machine
        self._tick_task = self.machine.clock.schedule_interval(self._tick, 1)
        self.screen = Screen.open()
        self.mpf_process = Process()
        self.ball_devices = list()      # type: List[BallDevice]

        self.switches = OrderedDict()   # type: Dict[Switch, Tuple[str, int, int]]
        self.player_start_row = 0
        self.column_positions = [0, .25, .5, .75]
        self.columns = [0] * len(self.column_positions)

        self.machine.events.add_handler('init_phase_2', self._init)
        self.machine.events.add_handler('init_phase_3', self._update_switches)
        # self.machine.events.add_handler('init_phase_3', self._init2)
        self.machine.events.add_handler('loading_assets',
                                        self._asset_load_change)
        self.machine.events.add_handler('bcp_connection_attempt',
                                        self._bcp_connection_attempt)
        self.machine.events.add_handler('asset_loading_complete',
                                        self._asset_load_complete)
        self.machine.events.add_handler('bcp_clients_connected',
                                        self._bcp_connected)
        self.machine.events.add_handler('shutdown', self.stop)
        self.machine.events.add_handler('player_number', self._update_player)
        self.machine.events.add_handler('player_ball', self._update_player)
        self.machine.events.add_handler('player_score', self._update_player)
        self.machine.events.add_handler('ball_ended',
                                        self._update_player_no_game)

        self._pending_bcp_connection = False
        self._asset_percent = 0
        self._bcp_status = (0, 0, 0)  # type: Tuple[float, int, int]

        self._draw_screen()
        self.screen.refresh()

    def _init(self, **kwargs):
        del kwargs
        self.machine.mode_controller.register_start_method(self._mode_change)
        self.machine.mode_controller.register_stop_method(self._mode_change)
        self.machine.switch_controller.add_monitor(self._update_switches)
        self.machine.bcp.interface.register_command_callback(
            "status_report", self._bcp_status_report)

        for bd in [x for x in self.machine.ball_devices if not x.is_playfield()]:
            self.ball_devices.append(bd)

        self.ball_devices.sort()
        self._draw_player_header()

        self._update_switch_layout()

    @asyncio.coroutine
    def _bcp_status_report(self, client, cpu, rss, vms):
        del client
        self._bcp_status = cpu, rss, vms

    def _draw_screen(self):

        for i, percent in enumerate(self.column_positions):
            if not i:
                self.columns[i] = 1
            self.columns[i] = int(self.screen.width * percent)

        height, width = self.screen.dimensions
        title = 'Mission Pinball Framework v{}'.format(mpf._version.__version__)    # noqa
        padding = int((self.screen.width - len(title)) / 2)

        self.screen.print_at((' ' * padding) + title + (' ' * (padding + 1)),
                             0, 0, colour=7, bg=1)

        self.screen.print_at('<CTRL+C> TO EXIT', width - 16, 0, colour=0, bg=1)

        self.screen.print_at('ACTIVE MODES', self.columns[0], 2)
        self.screen.print_at('SWITCHES', int((width * .5) - 8), 2)
        self.screen.print_at('BALL COUNTS', self.columns[3], 2)
        self.screen.print_at('-' * width, 0, 3)

        self.screen.print_at(self.machine.machine_path, 0, height - 2, colour=3)

        if 0 < self._asset_percent < 100:
            self.screen.print_at(' ' * width, 0, int(height / 2) + 1, bg=3)
            self.screen.print_at(
                'LOADING ASSETS: {}%'.format(self._asset_percent),
                int(width / 2) - 10, int(height / 2) + 1, colour=0, bg=3)

        if self._pending_bcp_connection:
            bcp_string = 'WAITING FOR MEDIA CONTROLLER {}...'.format(
                self._pending_bcp_connection)

            self.screen.print_at(' ' * width, 0, int(height / 2) - 1, bg=3)
            self.screen.print_at(
                bcp_string, int((width - len(bcp_string)) / 2),
                int(height / 2) - 1, colour=0, bg=3)

        self._update_stats()

    def _draw_player_header(self):
        self.player_start_row = (
            len(self.ball_devices) + len(self.machine.playfields)) + 7

        self.screen.print_at('CURRENT PLAYER', self.columns[3],
                             self.player_start_row - 2)
        self.screen.print_at('-' * (int(self.screen.width * .75) + 1),
                             self.columns[3],
                             self.player_start_row - 1)
        self._update_player()

    def _update_stats(self):
        height, width = self.screen.dimensions

        # Runtime
        rt = (datetime.now() - self.start_time)
        mins, sec = divmod(rt.seconds + rt.days * 86400, 60)
        hours, mins = divmod(mins, 60)
        time_string = 'RUNNING {:d}:{:02d}:{:02d}'.format(hours, mins, sec)
        self.screen.print_at(time_string, width - len(time_string),
                             height - 2, colour=2)

        # System Stats
        system_str = 'Free Memory (MB): {} CPU:{:3d}%'.format(
            round(virtual_memory().available / 1048576),
            round(cpu_percent(interval=None, percpu=False)))
        self.screen.print_at(system_str, width - len(system_str), height - 1,
                             colour=2)

        # MPF process stats
        stats_str = 'MPF (CPU RSS/VMS): {}% {}/{} MB    '.format(
            round(self.mpf_process.cpu_percent()),
            round(self.mpf_process.memory_info().rss / 1048576),
            round(self.mpf_process.memory_info().vms / 1048576))

        self.screen.print_at(stats_str, 0, height - 1, colour=6)

        # MC process stats
        if self._bcp_status != (0, 0, 0):
            bcp_string = 'MC (CPU RSS/VMS) {}% {}/{} MB '.format(
                round(self._bcp_status[0]),
                round(self._bcp_status[1] / 1048576),
                round(self._bcp_status[2] / 1048576))

            self.screen.print_at(bcp_string, len(stats_str) - 2, height - 1, colour=5)

    def _update_switch_layout(self):
        start_row = 4
        cutoff = int(len(self.machine.switches) / 2) + start_row - 1
        row = start_row
        col = 1

        for sw in sorted(self.machine.switches):
            if sw.invert:
                name = sw.name + '*'
            else:
                name = sw.name

            self.switches[sw] = (name, self.columns[col], row)

            if row == cutoff:
                row = start_row
                col += 1
            else:
                row += 1

        self._update_switches()

    def _update_switches(self, *args, **kwargs):
        del args, kwargs
        for sw, info in self.switches.items():
            if sw.state:
                self.screen.print_at(*info, colour=0, bg=2)
            else:
                self.screen.print_at(*info)

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
            self.screen.print_at(' ' * (self.columns[0] - 1),
                                 self.columns[0], i + 4)
            self.screen.print_at('{} ({})'.format(mode.name, mode.priority),
                                 self.columns[0], i + 4)

        self.screen.print_at(' ' * (int(self.screen.width * .25) - 1),
                             self.columns[0], len(modes) + 4)

    def _update_ball_devices(self, **kwargs):
        del kwargs

        row = 4

        try:
            for pf in self.machine.playfields:
                self.screen.print_at('{}: {} '.format(pf.name, pf.balls),
                                     self.columns[3], row,
                                     colour=2 if pf.balls else 7)
                row += 1
        except AttributeError:
            pass

        for bd in self.ball_devices:
            # extra spaces to overwrite previous chars if the str shrinks
            self.screen.print_at('{}: {} ({})                   '.format(
                bd.name, bd.balls, bd.state), self.columns[3], row,
                colour=2 if bd.balls else 7)
            row += 1

    def _update_player(self, **kwargs):
        del kwargs
        for i in range(3):
            self.screen.print_at(
                ' ' * (int(self.screen.width * (1 / len(self.columns))) + 1),
                self.columns[3],
                self.player_start_row + i)
        try:
            self.screen.print_at(
                'PLAYER: {}'.format(self.machine.game.player.number),
                self.columns[3], self.player_start_row)
            self.screen.print_at(
                'BALL: {}'.format(self.machine.game.player.ball),
                self.columns[3], self.player_start_row + 1)
            self.screen.print_at(
                'SCORE: {:,}'.format(self.machine.game.player.score),
                self.columns[3], self.player_start_row + 2)
        except AttributeError:
            self._update_player_no_game()

    def _update_player_no_game(self, **kwargs):
        del kwargs
        for i in range(3):
            self.screen.print_at(
                ' ' * (int(self.screen.width * (1 / len(self.columns))) + 1),
                self.columns[3],
                self.player_start_row + i)

        self.screen.print_at('NO GAME IN PROGRESS', self.columns[3],
                             self.player_start_row)

    def _tick(self):
        if self.screen.has_resized():
            self.screen = Screen.open()
            self._update_switch_layout()
            self._update_modes()
            self._draw_screen()
            self._draw_player_header()

        self.machine.bcp.transport.send_to_clients_with_handler(handler="_status_request",
                                                                bcp_command="status_request")
        self._update_stats()
        self._update_ball_devices()
        self.screen.refresh()

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

        self._update_modes()
        self._update_switches()
        self._update_ball_devices()

    def _asset_load_change(self, percent, **kwargs):
        del kwargs
        self._asset_percent = percent
        self._draw_screen()

    def _asset_load_complete(self, **kwargs):
        del kwargs
        self._asset_percent = 100
        self.screen.print_at(' ' * self.screen.width,
                             0, int(self.screen.height / 2) + 1)

        self._update_modes()
        self._update_switches()
        self._update_ball_devices()

    def stop(self, **kwargs):
        """Stop the Text UI and restore the original console screen."""
        del kwargs

        if self.screen:
            self.machine.clock.unschedule(self._tick_task)
            logger = logging.getLogger()
            logger.addHandler(logging.StreamHandler())
            self.screen.close(True)
