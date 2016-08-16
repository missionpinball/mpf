"""Service mode for MPF."""
import asyncio
from collections import namedtuple

from mpf.core.async_mode import AsyncMode

ServiceMenuEntry = namedtuple("ServiceMenuEntry", ["label", "callback"])


class Service(AsyncMode):

    """The service mode."""

    @staticmethod
    def get_config_spec():
        """Add validation for mode."""
        return '''
enter_events: list|str|
esc_events: list|str|
up_events: list|str|
down_events: list|str|
'''

    def _service_mode_exit(self):
        # this event starts attract mode again
        self.machine.events.post("service_mode_exited")
        self.machine.reset()

    @asyncio.coroutine
    def _get_key(self):
        event = yield from self.machine.events.wait_for_event_group_race({
            'ESC': self.config['mode_settings']['esc_events'],
            'ENTER': self.config['mode_settings']['enter_events'],
            'UP': self.config['mode_settings']['up_events'],
            'DOWN': self.config['mode_settings']['down_events']})
        return event['group']

    @asyncio.coroutine
    def _run(self):
        self.log.info("Service door opened.")
        self.machine.events.post("service_door_opened")

        try:
            while True:
                # wait for key
                key = yield from self._get_key()

                if key == "ENTER":
                    # start main menu
                    yield from self._start_main_menu()

                elif key == "UP":
                    # TODO: volume up
                    pass
                elif key == "DOWN":
                    # TODO: volume down
                    pass

        except asyncio.CancelledError:
            self.machine.events.post("service_door_closed")
            raise

    @asyncio.coroutine
    def _switch_test_menu(self):
        pass

    @asyncio.coroutine
    def _coil_test_menu(self):
        pass

    @asyncio.coroutine
    def _settings_menu(self):
        pass

    @asyncio.coroutine
    def _start_main_menu(self):
        self.log.info("Entered service mode. Resetting game if running. Resetting hardware interface now.")
        # this will stop attact and game mode
        self.machine.events.post("service_mode_entered")

        # TODO: reset hardware interface

        try:
            yield from self._service_mode_main_menu()
        except asyncio.CancelledError:
            # mode is stopping
            self._service_mode_exit()
            raise

        self._service_mode_exit()

    @asyncio.coroutine
    def _update_main_menu(self, items: [ServiceMenuEntry], position: int):
        self.machine.events.post("service_menu_selected", item=items[position].label)

    @asyncio.coroutine
    def _service_mode_main_menu(self):
        items = [
            ServiceMenuEntry("switch", self._switch_test_menu),
            ServiceMenuEntry("coil", self._coil_test_menu),
            ServiceMenuEntry("settings", self._settings_menu)
        ]
        position = 0
        self._update_main_menu(items, position)

        while True:
            key = yield from self._get_key()
            if key == 'ESC':
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
