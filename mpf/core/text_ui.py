"""Contains the TextUI class."""
from collections import defaultdict

from datetime import datetime
from psutil import cpu_percent, virtual_memory, Process

import mpf._version
from mpf.core.delays import DelayManager
from mpf.core.mpf_controller import MpfController

try:
    from asciimatics.scene import Scene
    from asciimatics.widgets import Frame, Layout, Label, Divider, PopUpDialog, Widget
    from asciimatics.widgets.utilities import THEMES
    from asciimatics.screen import Screen
except ImportError:
    Scene = None
    Frame = None
    Layout = object
    THEMES = None
    Label = None
    Divider = None
    PopUpDialog = None
    Widget = None
    Screen = None

MYPY = False
if MYPY:   # pragma: no cover
    from typing import List, Tuple, Dict  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports
    from mpf.devices.ball_device.ball_device \
        import BallDevice  # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports
    from mpf.devices.switch import Switch   # pylint: disable-msg=cyclic-import,unused-import,ungrouped-imports


class MpfLayout(Layout):

    """Add clear function."""

    def __init__(self, columns, fill_frame=False):
        """Store max_height."""
        self._columns = []
        super().__init__(columns, fill_frame)
        self.max_height = None

    def clear_columns(self):
        """Clear all columns."""
        self._columns = [[] for _ in self._columns]

    def set_max_height(self, max_height):
        """Set max height."""
        self.max_height = max_height

    def fix(self, start_x, start_y, max_width, max_height):
        """Limit height."""
        if self.max_height:
            return min(super().fix(start_x, start_y, max_width, max_height), self.max_height)

        return super().fix(start_x, start_y, max_width, max_height)


# pylint: disable-msg=too-many-instance-attributes
class TextUi(MpfController):

    """Handles the text-based UI."""

    config_name = "text_ui"

    __slots__ = ["start_time", "machine", "_tick_task", "screen", "mpf_process", "ball_devices", "switches",
                 "config", "_pending_bcp_connection", "_asset_percent", "_player_widgets", "_machine_widgets",
                 "_bcp_status", "frame", "layout", "scene", "footer_memory", "switch_widgets", "mode_widgets",
                 "ball_device_widgets", "footer_cpu", "footer_mc_cpu", "footer_uptime", "delay", "_layout_change"]

    def __init__(self, machine: "MachineController") -> None:
        """Initialize TextUi."""
        super().__init__(machine)
        self.delay = DelayManager(machine)
        self.config = machine.config.get('text_ui', {})

        self.screen = None

        if not machine.options['text_ui'] or not Scene:
            self.log.debug(f"Text UI is disabled. TUI option setting: {machine.options['text_ui']}, Asciimatics loaded: {Scene}")
            return

        # hack to add themes until https://github.com/peterbrittain/asciimatics/issues/207 is implemented
        THEMES["mpf_theme"] = defaultdict(
            lambda: (Screen.COLOUR_WHITE, Screen.A_NORMAL, Screen.COLOUR_BLACK),
            {
                "active_switch": (Screen.COLOUR_BLACK, Screen.A_NORMAL, Screen.COLOUR_GREEN),
                "pf_active": (Screen.COLOUR_GREEN, Screen.A_NORMAL, Screen.COLOUR_BLACK),
                "pf_inactive": (Screen.COLOUR_WHITE, Screen.A_NORMAL, Screen.COLOUR_BLACK),
                "label": (Screen.COLOUR_WHITE, Screen.A_NORMAL, Screen.COLOUR_BLACK),
                "title": (Screen.COLOUR_WHITE, Screen.A_NORMAL, Screen.COLOUR_RED),
                "title_exit": (Screen.COLOUR_BLACK, Screen.A_NORMAL, Screen.COLOUR_RED),
                "footer_cpu": (Screen.COLOUR_CYAN, Screen.A_NORMAL, Screen.COLOUR_BLACK),
                "footer_path": (Screen.COLOUR_YELLOW, Screen.A_NORMAL, Screen.COLOUR_BLACK),
                "footer_memory": (Screen.COLOUR_GREEN, Screen.A_NORMAL, Screen.COLOUR_BLACK),
                "footer_mc_cpu": (Screen.COLOUR_MAGENTA, Screen.A_NORMAL, Screen.COLOUR_BLACK),
            })

        self.start_time = datetime.now()
        self.machine = machine

        self.mpf_process = Process()
        self.ball_devices = list()      # type: List[BallDevice]

        self.switches = {}      # type: Dict[str, Switch]

        self.machine.events.add_handler('init_phase_2', self._init)
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
        self.machine.add_crash_handler(self.stop)
        self.machine.events.add_handler('player_number', self._update_player)
        self.machine.events.add_handler('player_ball', self._update_player)
        self.machine.events.add_handler('player_score', self._update_player)
        self.machine.events.add_handler('ball_ended',
                                        self._update_player)

        self._pending_bcp_connection = False
        self._asset_percent = 0
        self._bcp_status = (0, 0, 0)    # type: Tuple[float, int, int]
        self.switch_widgets = []        # type: List[Widget]
        self.mode_widgets = []          # type: List[Widget]
        self.ball_device_widgets = []   # type: List[Widget]
        self._machine_widgets = []      # type: List[Widget]
        self._player_widgets = []       # type: List[Widget]
        self.footer_memory = None
        self.footer_cpu = None
        self.footer_mc_cpu = None
        self.footer_uptime = None
        self._layout_change = True

        self._tick_task = self.machine.clock.schedule_interval(self._tick, 1)
        self._create_window()
        self._draw_screen()

    def _init(self, **kwargs):
        del kwargs
        for mode in self.machine.modes.values():
            self.machine.events.add_handler("mode_{}_started".format(mode.name), self._mode_change)
            self.machine.events.add_handler("mode_{}_stopped".format(mode.name), self._mode_change)

        self.machine.switch_controller.add_monitor(self._update_switches)
        self.machine.register_monitor("machine_vars", self._update_machine_vars)
        self.machine.variables.machine_var_monitor = True
        self.machine.bcp.interface.register_command_callback(
            "status_report", self._bcp_status_report)

        for bd in [x for x in self.machine.ball_devices.values() if not x.is_playfield()]:
            self.ball_devices.append(bd)

        self.ball_devices.sort()

        self._update_switch_layout()
        self._schedule_draw_screen()

    async def _bcp_status_report(self, client, cpu, rss, vms):
        del client
        self._bcp_status = cpu, rss, vms

    def _update_stats(self):
        # Runtime
        rt = (datetime.now() - self.start_time)
        mins, sec = divmod(rt.seconds + rt.days * 86400, 60)
        hours, mins = divmod(mins, 60)
        self.footer_uptime.text = 'RUNNING {:d}:{:02d}:{:02d}'.format(hours, mins, sec)

        # System Stats
        self.footer_memory.text = 'Free Memory (MB): {} CPU:{:3d}%'.format(
            round(virtual_memory().available / 1048576),
            round(cpu_percent(interval=None, percpu=False)))

        # MPF process stats
        self.footer_cpu.text = 'MPF (CPU RSS/VMS): {}% {}/{} MB    '.format(
            round(self.mpf_process.cpu_percent()),
            round(self.mpf_process.memory_info().rss / 1048576),
            round(self.mpf_process.memory_info().vms / 1048576))

        # MC process stats
        if self._bcp_status != (0, 0, 0):
            self.footer_mc_cpu.text = 'MC (CPU RSS/VMS) {}% {}/{} MB '.format(
                round(self._bcp_status[0]),
                round(self._bcp_status[1] / 1048576),
                round(self._bcp_status[2] / 1048576))
        else:
            self.footer_mc_cpu.text = ""

    def _update_switch_layout(self):
        num = 0
        self.switch_widgets = []
        self.switches = {}
        self.switch_widgets.append((Label("SWITCHES"), 1))
        self.switch_widgets.append((Divider(), 1))
        self.switch_widgets.append((Label(""), 2))
        self.switch_widgets.append((Divider(), 2))

        for sw in sorted(self.machine.switches.values()):
            if sw.invert:
                name = sw.name + '*'
            else:
                name = sw.name

            col = 1 if num <= int(len(self.machine.switches) / 2) else 2

            switch_widget = Label(name)
            if sw.state:
                switch_widget.custom_colour = "active_switch"

            self.switch_widgets.append((switch_widget, col))
            self.switches[sw.name] = (sw, switch_widget)

            num += 1

        self._schedule_draw_screen()

    def _update_switches(self, change, *args, **kwargs):
        del args
        del kwargs
        try:
            sw, switch_widget = self.switches[change.name]
        except KeyError:
            return
        if sw.state:
            switch_widget.custom_colour = "active_switch"
        else:
            switch_widget.custom_colour = "label"

        self._schedule_draw_screen()

    def _draw_switches(self):
        """Draw all switches."""
        for widget, column in self.switch_widgets:
            self.layout.add_widget(widget, column)

    def _mode_change(self, *args, **kwargs):
        # Have to call this on the next frame since the mode controller's
        # active list isn't updated yet
        del args
        del kwargs
        self.mode_widgets = []
        self.mode_widgets.append(Label("ACTIVE MODES"))
        self.mode_widgets.append(Divider())
        try:
            modes = self.machine.mode_controller.active_modes
        except AttributeError:
            modes = None

        if modes:
            for mode in modes:
                self.mode_widgets.append(Label('{} ({})'.format(mode.name, mode.priority)))
        else:
            self.mode_widgets.append(Label("No active modes"))

        # empty line at the end
        self.mode_widgets.append(Label(""))

        self._layout_change = True
        self._schedule_draw_screen()

    def _draw_modes(self):
        for widget in self.mode_widgets:
            self.layout.add_widget(widget, 0)

    def _draw_ball_devices(self):
        for widget in self.ball_device_widgets:
            self.layout.add_widget(widget, 3)

    def _update_ball_devices(self, **kwargs):
        del kwargs
        # TODO: do not create widgets. just update contents
        self.ball_device_widgets = []
        self.ball_device_widgets.append(Label("BALL COUNTS"))
        self.ball_device_widgets.append(Divider())

        try:
            for pf in self.machine.playfields.values():
                widget = Label('{}: {} '.format(pf.name, pf.balls))
                if pf.balls:
                    widget.custom_colour = "pf_active"
                else:
                    widget.custom_colour = "pf_inactive"
                self.ball_device_widgets.append(widget)

        except AttributeError:
            pass

        for bd in self.ball_devices:
            widget = Label('{}: {} ({})'.format(bd.name, bd.balls, bd.state))
            if bd.balls:
                widget.custom_colour = "pf_active"
            else:
                widget.custom_colour = "pf_inactive"

            self.ball_device_widgets.append(widget)

        self.ball_device_widgets.append(Label(""))

        self._layout_change = True
        self._schedule_draw_screen()

    def _update_player(self, **kwargs):
        del kwargs
        self._player_widgets = []
        self._player_widgets.append(Label("CURRENT PLAYER"))
        self._player_widgets.append(Divider())

        try:
            player = self.machine.game.player
            self._player_widgets.append(Label('PLAYER: {}'.format(player.number)))
            self._player_widgets.append(Label('BALL: {}'.format(player.ball)))
            self._player_widgets.append(Label('SCORE: {:,}'.format(player.score)))
        except AttributeError:
            self._player_widgets.append(Label("NO GAME IN PROGRESS"))
            return

        player_vars = player.vars.copy()
        player_vars.pop('score', None)
        player_vars.pop('number', None)
        player_vars.pop('ball', None)

        names = self.config.get('player_vars', player_vars.keys())
        for name in names:
            try:
                self.machine.events.replace_handler('player_' + name, self._update_player)
            except ValueError:
                pass
            self._player_widgets.append(Label("{}: {}".format(name, player_vars[name])))

        self._layout_change = True
        self._schedule_draw_screen()

    def _draw_player(self, **kwargs):
        del kwargs
        for widget in self._player_widgets:
            self.layout.add_widget(widget, 3)

    def _update_machine_vars(self, **kwargs):
        """Update machine vars."""
        del kwargs
        self._machine_widgets = []
        self._machine_widgets.append(Label("MACHINE VARIABLES"))
        self._machine_widgets.append(Divider())
        machine_vars = self.machine.variables.machine_vars
        # If config defines explict vars to show, only show those. Otherwise, all
        names = self.config.get('machine_vars', machine_vars.keys())
        for name in names:
            self._machine_widgets.append(Label("{}: {}".format(name, machine_vars[name]['value'])))
        self._layout_change = True
        self._schedule_draw_screen()

    def _draw_machine_variables(self):
        """Draw machine vars."""
        for widget in self._machine_widgets:
            self.layout.add_widget(widget, 0)

    def _create_window(self):
        self.screen = Screen.open()
        self.frame = Frame(self.screen, self.screen.height, self.screen.width, has_border=False, title="Test")
        self.frame.set_theme("mpf_theme")

        title_layout = Layout([1, 5, 1])
        self.frame.add_layout(title_layout)

        title_left = Label("")
        title_left.custom_colour = "title"
        title_layout.add_widget(title_left, 0)

        title = 'Mission Pinball Framework v{}'.format(mpf._version.__version__)    # noqa
        title_text = Label(title, align="^")
        title_text.custom_colour = "title"
        title_layout.add_widget(title_text, 1)

        exit_label = Label("< CTRL + C > TO EXIT", align=">")
        exit_label.custom_colour = "title_exit"

        title_layout.add_widget(exit_label, 2)

        self.layout = MpfLayout([1, 1, 1, 1], fill_frame=True)
        self.frame.add_layout(self.layout)

        footer_layout = Layout([1, 1, 1])
        self.frame.add_layout(footer_layout)
        self.footer_memory = Label("", align=">")
        self.footer_memory.custom_colour = "footer_memory"
        self.footer_uptime = Label("", align=">")
        self.footer_uptime.custom_colour = "footer_memory"
        self.footer_mc_cpu = Label("")
        self.footer_mc_cpu.custom_colour = "footer_mc_cpu"
        self.footer_cpu = Label("")
        self.footer_cpu.custom_colour = "footer_cpu"
        footer_path = Label(self.machine.machine_path)
        footer_path.custom_colour = "footer_path"
        footer_empty = Label("")
        footer_empty.custom_colour = "footer_memory"

        footer_layout.add_widget(footer_path, 0)
        footer_layout.add_widget(self.footer_cpu, 0)
        footer_layout.add_widget(footer_empty, 1)
        footer_layout.add_widget(self.footer_mc_cpu, 1)
        footer_layout.add_widget(self.footer_uptime, 2)
        footer_layout.add_widget(self.footer_memory, 2)

        self.scene = Scene([self.frame], -1)
        self.screen.set_scenes([self.scene], start_scene=self.scene)

        # prevent main from scrolling out the footer
        self.layout.set_max_height(self.screen.height - 2)

    def _schedule_draw_screen(self):
        # schedule the draw in 10ms if it is not scheduled
        self.delay.add_if_doesnt_exist(10, self._draw_screen, "draw_screen")

    def _draw_screen(self):
        if not self.screen:
            # probably drawing during game end
            return

        if self._layout_change:
            self.layout.clear_columns()
            self._draw_modes()
            self._draw_machine_variables()
            self._draw_switches()
            self._draw_ball_devices()
            self._draw_player()
            self.frame.fix()
            self._layout_change = False

        self.screen.force_update()
        self.screen.draw_next_frame()

    def _tick(self):
        if self.screen.has_resized():
            self._create_window()

        self._update_ball_devices()
        self._update_stats()

        self._schedule_draw_screen()

        self.machine.bcp.transport.send_to_clients_with_handler(handler="_status_request",
                                                                bcp_command="status_request")

    def _bcp_connection_attempt(self, name, host, port, **kwargs):
        del name
        del kwargs
        self._pending_bcp_connection = PopUpDialog(self.screen,
                                                   'WAITING FOR MEDIA CONTROLLER {}:{}'.format(host, port), [])
        self.scene.add_effect(self._pending_bcp_connection)
        self._schedule_draw_screen()

    def _bcp_connected(self, **kwargs):
        del kwargs
        self.scene.remove_effect(self._pending_bcp_connection)
        self._create_window()  # The MC will write any SDL or other messages on top of the TUI, so recreate it to get rid of that stuff
        self._schedule_draw_screen()

    def _asset_load_change(self, percent, **kwargs):
        del kwargs
        if self._asset_percent:
            self.scene.remove_effect(self._asset_percent)
        self._asset_percent = PopUpDialog(self.screen, 'LOADING ASSETS: {}%'.format(percent), [])
        self.scene.add_effect(self._asset_percent)
        self._schedule_draw_screen()

    def _asset_load_complete(self, **kwargs):
        del kwargs
        self.scene.remove_effect(self._asset_percent)
        self._schedule_draw_screen()

    def stop(self, **kwargs):
        """Stop the Text UI and restore the original console screen."""
        del kwargs
        if self.screen:
            self.machine.clock.unschedule(self._tick_task)
            self.screen.close(True)
            self.screen = None
