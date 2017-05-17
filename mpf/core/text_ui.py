"""Contains the TextUI class."""
from datetime import datetime
from typing import TYPE_CHECKING, Tuple
import psutil
from asciimatics.screen import Screen
from psutil import cpu_percent, virtual_memory
import mpf._version
from mpf.core.mpf_controller import MpfController

if TYPE_CHECKING:   # pragma: no cover
    from mpf.core.machine import MachineController


class TextUi(MpfController):
    """Handles the text-based UI"""

    def __init__(self, machine: "MachineController") -> None:
        """Initialize TextUi."""

        super().__init__(machine)

        self.screen = None

        if not machine.options['text_ui']:
            return

        self.start_time = datetime.now()
        self.machine = machine
        self.machine.clock.schedule_interval(self._tick, 1)
        self.screen = Screen.open()
        self.mpf_process = psutil.Process()

        self.machine.events.add_handler('init_phase_1', self._init)
        self.machine.events.add_handler('init_phase_3', self._update_switches)
        self.machine.events.add_handler('init_phase_3', self._init2)
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
        self._bcp_status = (0, 0, 0)  # type: Tuple[float, int, int]

        self._draw_screen()

    def _init(self, **kwargs):
        del kwargs
        self.machine.mode_controller.register_start_method(self._mode_change)
        self.machine.mode_controller.register_stop_method(self._mode_change)
        self.machine.switch_controller.add_monitor(self._update_switches)
        self.machine.bcp.interface.register_command_callback(
            "status_report", self._bcp_status_report)

    def _init2(self, **kwargs):
        del kwargs

        for bd in self.machine.ball_devices:
            self.machine.events.add_handler(
                'balldevice_{}_ball_enter'.format(bd.name),
                self._update_ball_devices)

        self._update_ball_devices(0, 0, None)

    def _bcp_status_report(self, client, cpu, rss, vms):
        del client
        self._bcp_status = cpu, rss, vms

    def _draw_screen(self):
        height, width = self.screen.dimensions
        title = 'Mission Pinball Framework v{}'.format(
            mpf._version.__version__)
        padding = int((self.screen.width - len(title)) / 2)

        self.screen.print_at((' ' * padding) + title + (' ' * (padding + 1)),
                             0, 0, colour=7, bg=1)

        self.screen.print_at('<CTRL+C> TO EXIT', width-16, 0, colour=0, bg=1)

        self.screen.print_at('ACTIVE MODES', 1, 2)
        self.screen.print_at('ACTIVE SWITCHES', int(width * .33), 2)
        self.screen.print_at('BALL COUNTS', int(width * .66), 2)
        self.screen.print_at('-' * width, 0, 3)

        self.screen.print_at(self.machine.machine_path, 0, height-2, colour=3)

        if 0 < self._asset_percent < 100:
            self.screen.print_at(
                'LOADING ASSETS: {}%'.format(self._asset_percent),
                int(width / 2) - 10, int(height / 2) + 1, colour=0, bg=3)

        if self._pending_bcp_connection:
            bcp_string = 'WAITING FOR MEDIA CONTROLLER {}...'.format(
                self._pending_bcp_connection)

            self.screen.print_at(
                bcp_string, int((width - len(bcp_string)) / 2),
                int(height / 2) - 1, colour=0, bg=3)

        self._update_stats()

    def _update_stats(self):
        height, width = self.screen.dimensions

        # Runtime
        rt = (datetime.now() - self.start_time)
        mins, sec = divmod(rt.seconds + rt.days * 86400, 60)
        hours, mins = divmod(mins, 60)
        time_string = 'RUNNING {:d}:{:02d}:{:02d}'.format(hours, mins, sec)
        self.screen.print_at(time_string, width - len(time_string),
                             height-2, colour=2)

        # System Stats
        system_str = 'Free Memory (MB): {} CPU:{:3d}%'.format(
            round(virtual_memory().available / 1048576),
            round(cpu_percent(interval=None, percpu=False)))
        self.screen.print_at(system_str, width-len(system_str), height-1,
                             colour=2)

        # MPF process stats
        stats_str = 'MPF (CPU RSS/VMS): {}% {}/{} MB    '.format(
            round(self.mpf_process.cpu_percent()),
            round(self.mpf_process.memory_info().rss / 1048576),
            round(self.mpf_process.memory_info().vms / 1048576))

        self.screen.print_at(stats_str, 0, height-1, colour=6)

        # MC process stats
        if self._bcp_status != (0, 0, 0):
            bcp_string = 'MC (CPU RSS/VMS) {}% {}/{} MB'.format(
                round(self._bcp_status[0]),
                round(self._bcp_status[1] / 1048576),
                round(self._bcp_status[2] / 1048576))

            self.screen.print_at(bcp_string,
                len(stats_str) - 2, height-1, colour=5)

        self.screen.refresh()

    def _update_switches(self, *args, **kwargs):
        del args
        del kwargs
        switches = sorted(list(
            x.name for x in self.machine.switches if x.state))

        x_pos = int(self.screen.width * .33)

        for i, switch in enumerate(switches):
            self.screen.print_at(' ' * x_pos, x_pos, i+4)
            self.screen.print_at(switch, x_pos, i+4)

        self.screen.print_at(' ' * x_pos, x_pos, len(switches)+4)
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
            self.screen.print_at(' ' * (int(self.screen.width * .33) - 1),
                                 1, i+4)
            self.screen.print_at('{} ({})'.format(mode.name, mode.priority),
                                 1, i+4)

        self.screen.print_at(' ' * (int(self.screen.width * .33) - 1),
                             1, len(modes) + 4)
        self.screen.refresh()

    def _update_ball_devices(self, new_balls, unclaimed_balls, device,
                             **kwargs):
        del kwargs

        bd_list = list()
        for bd in self.machine.ball_devices:
            try:
                bd_list.append((bd.name, bd.balls, '({})'.format(bd.state)))
            except AttributeError:
                bd_list.append((bd.name, bd.balls, ''))

        x_pos = int(self.screen.width * .66)

        for i, bd in enumerate(sorted(bd_list, key=lambda x: x[2])):

            # extra spaces to overwrite previous chars if the str shrinks
            self.screen.print_at('{}: {} {}                   '.format(
                bd[0], bd[1], bd[2]), x_pos, i+4)

        return dict(unclaimed_balls=unclaimed_balls, new_balls=new_balls,
                    device=device)

    def _tick(self):
        if self.screen.has_resized():
            self.screen = Screen.open()
            self._draw_screen()
            self._update_switches()
            self._update_modes()

        else:
            self._update_stats()

        # request status from all bcp clients
        self.machine.bcp.transport.send_to_all_clients("status_request")

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
