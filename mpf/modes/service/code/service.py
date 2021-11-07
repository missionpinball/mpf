"""Service mode for MPF."""
import subprocess
import os
from collections import namedtuple
from functools import partial

from typing import List

from mpf.core.async_mode import AsyncMode
from mpf.core.switch_controller import MonitoredSwitchChange
from mpf.core.utility_functions import Util

ServiceMenuEntry = namedtuple("ServiceMenuEntry", ["label", "callback"])


class Service(AsyncMode):

    """The service mode."""

    __slots__ = ["_update_script", "_do_sort"]

    def __init__(self, *args, **kwargs):
        """Initialize service mode."""
        super().__init__(*args, **kwargs)
        self._update_script = None
        self._do_sort = self.config.get('mode_settings', {}).get('sort_devices_by_number', True)

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
software_update: single|bool|False
software_update_script: single|str|None
sort_devices_by_number: single|bool|True
'''

    async def _service_mode_exit(self):
        await self.machine.service.stop_service()

    def _get_key(self):
        return Util.race({
            self.machine.events.wait_for_any_event(self.config['mode_settings']['esc_events']): "ESC",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['enter_events']): "ENTER",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['up_events']): "UP",
            self.machine.events.wait_for_any_event(self.config['mode_settings']['down_events']): "DOWN",
        })

    async def _run(self):
        while True:
            # wait for key
            key = await self._get_key()

            if key == "ENTER":
                # start main menu
                await self._start_main_menu()
            elif key == "UP":
                volume = self.machine.variables.get_machine_var("master_volume")
                if not isinstance(volume, float):
                    volume = .5
                volume += .1
                if volume >= 1.0:
                    volume = 1.0
                else:
                    volume = round(volume, 1)
                self.machine.variables.set_machine_var("master_volume", volume)
                # post event for increased volume
                self.machine.events.post("master_volume_increase", volume=volume)
                '''event: master_volume_increase

                desc: Increase the master volume of the audio system.

                args:

                volume: New volume as float between 0.0 an 1.0
                '''
            elif key == "DOWN":
                volume = self.machine.variables.get_machine_var("master_volume")
                if not isinstance(volume, float):
                    volume = .5
                volume -= .1
                if volume <= 0.0:
                    volume = 0.0
                else:
                    volume = round(volume, 1)
                self.machine.variables.set_machine_var("master_volume", volume)
                # post event for decreased volume
                self.machine.events.post("master_volume_decrease", volume=volume)
                '''event: master_volume_decrease

                desc: Decrease the master volume of the audio system.

                args:

                volume: New volume as float between 0.0 an 1.0
                '''

    async def _start_main_menu(self):
        self.machine.service.start_service()
        self.machine.events.post("service_main_menu")
        await self._service_mode_main_menu()

        await self._service_mode_exit()

    def _update_main_menu(self, items: List[ServiceMenuEntry], position: int):
        self.machine.events.post("service_menu_deselected")
        self.machine.events.post("service_menu_show")
        self.machine.events.post("service_menu_selected", label=items[position].label)

    def _load_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the menu items with label and callback."""
        # If you want to add menu entries overload the mode and this method.
        entries = [
            ServiceMenuEntry("Diagnostics Menu", self._diagnostics_menu),
            ServiceMenuEntry("Audits Menu", self._audits_menu),
            ServiceMenuEntry("Adjustments Menu", self._adjustments_menu),
            ServiceMenuEntry("Utilities Menu", self._utilities_menu),

        ]
        return entries

    async def _service_mode_main_menu(self):
        """Show main menu."""
        await self._make_menu(self._load_menu_entries())
        # hide slides on exit
        self.machine.events.post("service_menu_hide")

    # Diagnostics
    def _load_diagnostic_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the diagnostics menu items with label and callback."""
        return [
            ServiceMenuEntry("Switch Menu", self._diagnostics_switch_menu),
            ServiceMenuEntry("Coil Menu", self._diagnostics_coil_menu),
            ServiceMenuEntry("Light Menu", self._diagnostics_light_menu),
        ]

    async def _diagnostics_menu(self):
        await self._make_menu(self._load_diagnostic_menu_entries())

    def _load_diagnostic_switch_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the switch menu items with label and callback."""
        return [
            ServiceMenuEntry("Switch Edge Test", self._switch_test_menu),
        ]

    async def _diagnostics_switch_menu(self):
        await self._make_menu(self._load_diagnostic_switch_menu_entries())

    def _load_diagnostic_coil_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the coil menu items with label and callback."""
        return [
            ServiceMenuEntry("Single Coil Test", self._coil_test_menu),
        ]

    async def _diagnostics_coil_menu(self):
        await self._make_menu(self._load_diagnostic_coil_menu_entries())

    def _load_diagnostic_light_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the light menu items with label and callback."""
        return [
            ServiceMenuEntry("Single Light Test", self._light_test_menu),
        ]

    async def _diagnostics_light_menu(self):
        await self._make_menu(self._load_diagnostic_light_menu_entries())

    # Adjustments
    def _load_adjustments_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the adjustments menu items with label and callback."""
        return [
            ServiceMenuEntry("Standard Adjustments", partial(self._settings_menu, "standard")),
            ServiceMenuEntry("Feature Adjustments", partial(self._settings_menu, "feature")),
            ServiceMenuEntry("Game Adjustments", partial(self._settings_menu, "game")),
            ServiceMenuEntry("Coin Adjustments", partial(self._settings_menu, "coin")),
        ]

    async def _adjustments_menu(self):
        await self._make_menu(self._load_adjustments_menu_entries())

    # Utilities
    def _load_utilities_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the utilities menu items with label and callback."""
        entries = [
            ServiceMenuEntry("Reset Menu", self._utilities_reset_menu),
        ]

        if self.config['mode_settings']['software_update']:
            update_file_path = self.config['mode_settings']['software_update_script']
            if not update_file_path:
                raise AssertionError("Please configure software_update_script to enable software_update in "
                                     "service mode.")

            if not os.path.isabs(update_file_path):
                update_file_path = os.path.join(self.machine.machine_path, update_file_path)

            if os.path.isfile(update_file_path):
                self._update_script = update_file_path
                entries.append(ServiceMenuEntry("Software Update", self._software_update))

        return entries

    async def _utilities_menu(self):
        await self._make_menu(self._load_utilities_menu_entries())

    def _load_utilities_reset_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the utilities reset menu items with label and callback."""
        return [
            ServiceMenuEntry("Reset Coin Audits", self._utilities_reset_coin_audits),
            ServiceMenuEntry("Reset Game Audits", self._utilities_reset_game_audits),
            ServiceMenuEntry("Reset High Scores", self._utilities_reset_high_scores),
            ServiceMenuEntry("Reset Credits", self._utilities_reset_credits),
            ServiceMenuEntry("Reset to Factory Settings", self._utilities_reset_to_factory_settings),
        ]

    async def _make_option_slide(self, title, question, options, warning):
        """Show service_options_slide, provide options and return the selected option."""
        position = 0

        while True:
            self.machine.events.post("service_options_slide_start", title=title, question=question,
                                     option=options[position], warning=warning)
            key = await self._get_key()
            if key == 'ESC':
                self.machine.events.post("service_options_slide_stop")
                return None
            if key == 'UP':
                position += 1
                if position >= len(options):
                    position = 0
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(options) - 1
            elif key == 'ENTER':
                # select and return option
                self.machine.events.post("service_options_slide_stop")
                return options[position]

    async def _utilities_reset_menu(self):
        await self._make_menu(self._load_utilities_reset_menu_entries())

    async def _utilities_reset_coin_audits(self):
        selection = await self._make_option_slide("Reset earning audits", "Perform coin reset?", ["no", "yes"],
                                                  "THIS CANNOT BE UNDONE")
        if selection == "yes":
            self.machine.events.post("earnings_reset")

    async def _utilities_reset_game_audits(self):
        selection = await self._make_option_slide("Auditor Reset", "Reset Game Audits?", ["no", "yes"],
                                                  "THIS CANNOT BE UNDONE")
        if selection == "yes":
            self.machine.events.post("auditor_reset")

    async def _utilities_reset_high_scores(self):
        selection = await self._make_option_slide("High Score Reset", "Remove Highscores?", ["no", "yes"],
                                                  "THIS CANNOT BE UNDONE")
        if selection == "yes":
            self.machine.events.post("high_scores_reset")

    async def _utilities_reset_credits(self):
        selection = await self._make_option_slide("Reset credits", "Remove all credits?", ["no", "yes"],
                                                  "THIS CANNOT BE UNDONE")
        if selection == "yes":
            self.machine.events.post("credits_reset")

    async def _utilities_reset_to_factory_settings(self):
        selection = await self._make_option_slide("Factory Reset", "Reset to factory setting?", ["no", "yes"],
                                                  "THIS CANNOT BE UNDONE")
        if selection == "yes":
            self.machine.events.post("factory_reset")

    async def _software_update(self):
        run_update = False
        self._update_software_update_slide(run_update)

        while True:
            key = await self._get_key()
            if key == 'ESC':
                break
            if key in ('UP', 'DOWN'):
                run_update = not run_update
                self._update_software_update_slide(run_update)
            elif key == 'ENTER' and run_update:
                # perform update
                self.machine.events.post("service_software_update_start")
                subprocess.Popen([self._update_script])
                self.machine.stop("Software Update")

        self.machine.events.post("service_software_update_stop")

    def _update_software_update_slide(self, run_update):
        self.machine.events.post("service_software_update_choice", run_update="Yes" if run_update else "No")

    async def _make_menu(self, items):
        """Show a menu by controlling slides via events and executing callbacks."""
        if not items:
            # do not crash on empty menu
            return
        position = 0
        self._update_main_menu(items, position)

        while True:
            key = await self._get_key()
            if key == 'ESC':
                return
            if key == 'UP':
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
                self.machine.events.post("service_menu_deselected")
                await items[position].callback()
                self._update_main_menu(items, position)

    def _switch_monitor(self, change: MonitoredSwitchChange):
        if change.state:
            state_string = "active"
            self.machine.events.post("service_switch_hit")
        else:
            state_string = "inactive"

        label_string = "" if change.label == "%" else change.label

        self.machine.events.post("service_switch_test_start",
                                 switch_name=change.name,
                                 switch_num=change.num,
                                 switch_label=label_string,
                                 switch_state=state_string)

    async def _switch_test_menu(self):
        self.machine.switch_controller.add_monitor(self._switch_monitor)
        self.machine.events.post("service_switch_test_start",
                                 switch_name="", switch_state="", switch_num="", switch_label="")
        await self.machine.events.wait_for_any_event(self.config['mode_settings']['esc_events'])
        self.machine.events.post("service_switch_test_stop")
        self.machine.switch_controller.remove_monitor(self._switch_monitor)

    def _update_coil_slide(self, items, position):
        board, coil = items[position]
        self.machine.events.post("service_coil_test_start",
                                 board_name=board,
                                 coil_name=coil.name,
                                 coil_label=coil.config['label'],
                                 coil_num=coil.hw_driver.number)

    async def _coil_test_menu(self):
        position = 0
        items = self.machine.service.get_coil_map(do_sort=self._do_sort)

        # do not crash if no coils are configured
        if not items:   # pragma: no cover
            return

        self._update_coil_slide(items, position)

        while True:
            key = await self._get_key()
            if key == 'ESC':
                break
            if key == 'UP':
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
        label_string = "" if light.config['label'] == "%" else light.config['label']
        self.machine.events.post("service_light_test_start",
                                 board_name=board,
                                 light_name=light.name,
                                 light_label=label_string,
                                 light_num=light.config['number'],
                                 test_color=color)

    async def _light_test_menu(self):
        position = 0
        color_position = 0
        colors = ["white", "red", "green", "blue", "yellow"]
        items = self.machine.service.get_light_map(do_sort=self._do_sort)

        # do not crash if no lights are configured
        if not items:   # pragma: no cover
            return

        self._update_light_slide(items, position, colors[color_position])

        while True:
            self._update_light_slide(items, position, colors[color_position])
            items[position].light.color(colors[color_position], key="service", priority=1000000)

            key = await self._get_key()
            items[position].light.remove_from_stack_by_key("service")
            if key == 'ESC':
                break
            if key == 'UP':
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

    def _load_audit_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the audit menu items with label and callback."""
        return [
            ServiceMenuEntry("Earning Audits", self._audit_earning_menu),
            ServiceMenuEntry("Switch Audits", self._audit_switch_menu),
            ServiceMenuEntry("Shot Audits", self._audit_shot_menu),
            ServiceMenuEntry("Event Audits", self._audit_event_menu),
            ServiceMenuEntry("Player Audits", self._audit_player_menu),
        ]

    async def _audits_menu(self):
        await self._make_menu(self._load_audit_menu_entries())

    def _update_audits_slide(self, items, position):
        item = items[position][0]
        value = items[position][1]
        self.machine.events.post("service_audits_menu_show", audits_label=str(item), value_label=str(value))

    async def _audits_submenu(self, items):
        position = 0
        if not items:   # pragma: no cover
            return
        self._update_audits_slide(items, position)
        while True:
            key = await self._get_key()
            if key == 'ESC':
                break
            if key == 'UP':
                position += 1
                if position >= len(items):
                    position = 0
                self._update_audits_slide(items, position)
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(items) - 1
                self._update_audits_slide(items, position)
            if key == 'ENTER':
                # fallthrough
                pass
        self.machine.events.post("service_audits_menu_hide")

    async def _audit_earning_menu(self):
        try:
            items = self.machine.modes['credits'].earnings
        except (IndexError, KeyError):
            items = {}

        await self._audits_submenu(list(items.items()))

    async def _audit_player_menu(self):
        audits = self.machine.auditor.current_audits.get('player', {})

        items = []
        for audit, audit_values in audits.items():
            for key, value in audit_values.items():
                items.append(("{} {}".format(audit, key), value))

        await self._audits_submenu(items)

    async def _audit_switch_menu(self):
        items = self.machine.auditor.current_audits.get('switches', {})
        await self._audits_submenu(list(items.items()))

    async def _audit_shot_menu(self):
        items = self.machine.auditor.current_audits.get('shots', {})
        await self._audits_submenu(list(items.items()))

    async def _audit_event_menu(self):
        items = self.machine.auditor.current_audits.get('events', {})
        await self._audits_submenu(list(items.items()))

    def _update_settings_slide(self, items, position, is_change=False):
        setting = items[position]
        label = self.machine.settings.get_setting_value_label(setting.name)
        event = "service_settings_{}".format("edit" if is_change else "start")
        self.machine.events.post(event,
                                 settings_label=setting.label,
                                 value_label=label)

    async def _settings_menu(self, settings_type):
        position = 0
        items = self.machine.settings.get_settings(settings_type)

        # do not crash if no settings
        if not items:   # pragma: no cover
            return

        self._update_settings_slide(items, position)

        while True:
            key = await self._get_key()
            if key == 'ESC':
                break
            if key == 'UP':
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
                await self._settings_change(items, position)

        self.machine.events.post("service_settings_stop")

    async def _settings_change(self, items, position):
        self._update_settings_slide(items, position)

        values = list(items[position].values.keys())
        value_position = values.index(self.machine.settings.get_setting_value(items[position].name))
        self._update_settings_slide(items, position, is_change=True)

        while True:
            key = await self._get_key()
            if key == 'ESC':
                self._update_settings_slide(items, position)
                break
            if key == 'UP':
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
