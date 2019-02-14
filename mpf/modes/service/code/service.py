"""Service mode for MPF."""
import asyncio
from collections import namedtuple

from typing import List

from mpf.core.async_mode import AsyncMode
from mpf.core.switch_controller import MonitoredSwitchChange
from mpf.core.utility_functions import Util

ServiceMenuEntry = namedtuple("ServiceMenuEntry", ["label", "callback"])


class Service(AsyncMode):

    """The service mode."""

    __slots__ = []

    @staticmethod
    def get_config_spec():
        """Add validation for mode."""
        return '''
door_opened_events: list|str|service_door_opened
door_closed_events: list|str|service_door_closed
high_power_on_events: list|str|service_power_on
high_power_off_events: list|str|service_power_off
enter_events: list|str|sw_service_enter_active
esc_events: list|str|sw_service_esc_active
up_events: list|str|sw_service_up_active
down_events: list|str|sw_service_down_active
'''

    @asyncio.coroutine
    def _service_mode_exit(self):
        yield from self.machine.service.stop_service()

    def _get_key(self):
        return Util.race({
            self.machine.events.wait_for_any_event(self.config['mode_settings']['esc_events']): "ESC",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['enter_events']): "ENTER",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['up_events']): "UP",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['down_events']): "DOWN",
        }, self.machine.clock.loop)

    @asyncio.coroutine
    def _run(self):
        while True:
            # wait for key
            key = yield from self._get_key()

            if key == "ENTER":
                # start main menu
                yield from self._start_main_menu()
            elif key == "UP":
                # post event for mc to increase volume
                self.machine.events.post("master_volume_increase")
                '''event: master_volume_increase

                desc: Increase the master volume of the audio system.
                '''
            elif key == "DOWN":
                # post event for mc to decrease volume
                self.machine.events.post("master_volume_decrease")
                '''event: master_volume_decrease

                desc: Decrease the master volume of the audio system.
                '''

    @asyncio.coroutine
    def _start_main_menu(self):
        self.machine.service.start_service()
        self.machine.events.post("service_main_menu")
        yield from self._service_mode_main_menu()

        yield from self._service_mode_exit()

    def _update_main_menu(self, items: List[ServiceMenuEntry], position: int):
        self.machine.events.post("service_menu_deselected")
        self.machine.events.post("service_menu_show")
        self.machine.events.post("service_menu_selected_{}".format(items[position].label))

    def _load_menu_entries(self):
        """Return the menu items wich label and callback."""
        # If you want to add menu entries overload the mode and this method.
        return [
            ServiceMenuEntry("switch", self._switch_test_menu),
            ServiceMenuEntry("coil", self._coil_test_menu),
            ServiceMenuEntry("light", self._light_test_menu),
            ServiceMenuEntry("settings", self._settings_menu)
        ]

    @asyncio.coroutine
    def _service_mode_main_menu(self):
        items = self._load_menu_entries()
        position = 0
        self._update_main_menu(items, position)

        while True:
            key = yield from self._get_key()
            if key == 'ESC':
                self.machine.events.post("service_menu_hide")
                return
            elif key == 'UP':
                position += 1
                if position >= len(items):
                    position = 0
                self._update_main_menu(items, position)
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(items) - 1
                self._update_main_menu(items, position)
            elif key == 'ENTER':
                # call submenu
                yield from items[position].callback()
                self._update_main_menu(items, position)

    def _switch_monitor(self, change: MonitoredSwitchChange):
        if change.state:
            state_string = "active"
            self.machine.events.post("service_switch_hit")
        else:
            state_string = "inactive"

        self.machine.events.post("service_switch_test_start",
                                 switch_name=change.name,
                                 switch_num=change.num,
                                 switch_label=change.label,
                                 switch_state=state_string)

    @asyncio.coroutine
    def _switch_test_menu(self):
        self.machine.switch_controller.add_monitor(self._switch_monitor)
        self.machine.events.post("service_switch_test_start",
                                 switch_name="", switch_state="", switch_num="", switch_label="")
        yield from self.machine.events.wait_for_any_event(self.config['mode_settings']['esc_events'])
        self.machine.events.post("service_switch_test_stop")
        self.machine.switch_controller.remove_monitor(self._switch_monitor)

    def _update_coil_slide(self, items, position):
        board, coil = items[position]
        self.machine.events.post("service_coil_test_start",
                                 board_name=board,
                                 coil_name=coil.name,
                                 coil_label=coil.config['label'],
                                 coil_num=coil.hw_driver.number)

    @asyncio.coroutine
    def _coil_test_menu(self):
        position = 0
        items = self.machine.service.get_coil_map()

        # do not crash if no coils are configured
        if not items:   # pragma: no cover
            return

        self._update_coil_slide(items, position)

        while True:
            key = yield from self._get_key()
            if key == 'ESC':
                break
            elif key == 'UP':
                position += 1
                if position >= len(items):
                    position = 0
                self._update_coil_slide(items, position)
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(items) - 1
                self._update_coil_slide(items, position)
            elif key == 'ENTER':
                # pulse coil
                items[position].coil.pulse()

        self.machine.events.post("service_coil_test_stop")

    def _update_light_slide(self, items, position, color):
        board, light = items[position]
        self.machine.events.post("service_light_test_start",
                                 board_name=board,
                                 light_name=light.name,
                                 light_label=light.config['label'],
                                 light_num=light.config['number'],
                                 test_color=color)

    @asyncio.coroutine
    def _light_test_menu(self):
        position = 0
        color_position = 0
        colors = ["white", "red", "green", "blue", "yellow"]
        items = self.machine.service.get_light_map()

        # do not crash if no lights are configured
        if not items:   # pragma: no cover
            return

        self._update_light_slide(items, position, colors[color_position])

        while True:
            self._update_light_slide(items, position, colors[color_position])
            items[position].light.color(colors[color_position], key="service", priority=1000000)

            key = yield from self._get_key()
            items[position].light.remove_from_stack_by_key("service")
            if key == 'ESC':
                break
            elif key == 'UP':
                position += 1
                if position >= len(items):
                    position = 0
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(items) - 1
            elif key == 'ENTER':
                # change color
                color_position += 1
                if color_position >= len(colors):
                    color_position = 0

        self.machine.events.post("service_light_test_stop")

    def _update_settings_slide(self, items, position, is_change=False):
        setting = items[position]
        label = self.machine.settings.get_setting_value_label(setting.name)
        event = "service_settings_{}".format("edit" if is_change else "start")
        self.machine.events.post(event,
                                 settings_label=setting.label,
                                 value_label=label)

    @asyncio.coroutine
    def _settings_menu(self):
        position = 0
        items = self.machine.settings.get_settings()

        # do not crash if no settings
        if not items:   # pragma: no cover
            return

        self._update_settings_slide(items, position)

        while True:
            key = yield from self._get_key()
            if key == 'ESC':
                break
            elif key == 'UP':
                position += 1
                if position >= len(items):
                    position = 0
                self._update_settings_slide(items, position)
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(items) - 1
                self._update_settings_slide(items, position)
            elif key == 'ENTER':
                # change setting
                yield from self._settings_change(items, position)

        self.machine.events.post("service_settings_stop")

    @asyncio.coroutine
    def _settings_change(self, items, position):
        self._update_settings_slide(items, position)

        values = list(items[position].values.keys())
        value_position = values.index(self.machine.settings.get_setting_value(items[position].name))
        self._update_settings_slide(items, position, is_change=True)

        while True:
            key = yield from self._get_key()
            if key == 'ESC':
                self._update_settings_slide(items, position)
                break
            elif key == 'UP':
                value_position += 1
                if value_position >= len(values):
                    value_position = 0
                self.machine.settings.set_setting_value(items[position].name, values[value_position])
                self._update_settings_slide(items, position, is_change=True)
            elif key == 'DOWN':
                value_position -= 1
                if value_position < 0:
                    value_position = len(values) - 1
                self.machine.settings.set_setting_value(items[position].name, values[value_position])
                self._update_settings_slide(items, position, is_change=True)
