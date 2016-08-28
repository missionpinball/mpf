"""Service mode for MPF."""
import asyncio
from collections import namedtuple

from mpf.core.async_mode import AsyncMode
from mpf.core.utility_functions import Util

ServiceMenuEntry = namedtuple("ServiceMenuEntry", ["label", "callback"])


class Service(AsyncMode):

    """The service mode."""

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

    def _service_mode_exit(self):
        self.machine.service.stop_service()

    def _get_key(self):
        return Util.race({
            self.machine.events.wait_for_any_event(self.config['mode_settings']['esc_events']): "ESC",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['enter_events']): "ENTER",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['up_events']): "UP",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['down_events']): "DOWN",
        }, self.machine.clock.loop)

    def _register_service_door_handler(self):
        for switch in self.config['mode_settings']['door_open_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._service_door_handler, state=1, return_info=True)
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._service_door_handler, state=0, return_info=True)

    def _service_door_handler(self, state, **kwargs):
        del kwargs
        if state == 1:
            self.machine.events.post("service_door_opened")
        else:
            self.machine.events.post("service_door_closed")

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
            elif key == "DOWN":
                # post event for mc to decrease volume
                self.machine.events.post("master_volume_decrease")

    @asyncio.coroutine
    def _start_main_menu(self):
        self.machine.service.start_service()
        self.machine.events.post("service_main_menu")
        try:
            yield from self._service_mode_main_menu()
        except asyncio.CancelledError:
            # mode is stopping
            self._service_mode_exit()
            raise

        self._service_mode_exit()

    def _update_main_menu(self, items: [ServiceMenuEntry], position: int):
        self.machine.events.post("service_menu_show")
        self.machine.events.post("service_menu_selected_{}".format(items[position].label))

    def _load_menu_entries(self):
        """Return the menu items wich label and callback."""
        # If you want to add menu entries overload the mode and this method.
        return [
            ServiceMenuEntry("switch", self._switch_test_menu),
            ServiceMenuEntry("coil", self._coil_test_menu),
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

    @asyncio.coroutine
    def _switch_test_menu(self):
        pass

    @asyncio.coroutine
    def _coil_test_menu(self):
        pass

    @asyncio.coroutine
    def _settings_menu(self):
        pass
