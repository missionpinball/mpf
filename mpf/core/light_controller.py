"""Handles all light updates."""
import asyncio

from typing import Dict, Optional

from mpf.core.machine import MachineController
from mpf.core.settings_controller import SettingEntry

from mpf.core.rgb_color import RGBColorCorrectionProfile, RGBColor

from mpf.core.mpf_controller import MpfController
from mpf.core.utility_functions import Util


class LightController(MpfController):

    """Handles light updates and light monitoring."""

    __slots__ = ["light_color_correction_profiles", "_initialised", "_monitor_update_task", "brightness_factor",
                 "_brightness_template"]

    config_name = "light_controller"

    def __init__(self, machine: MachineController) -> None:
        """Initialise lights controller."""
        super().__init__(machine)

        # Generate and add color correction profiles to the machine
        self.light_color_correction_profiles = dict()       # type: Dict[str, RGBColorCorrectionProfile]

        # will only get initialised if there are lights
        self._initialised = False
        self._brightness_template = self.machine.placeholder_manager.build_float_template("machine.brightness", 1.0)
        self._update_brightness()

        self._monitor_update_task = None                    # type: Optional[asyncio.Task]

        if 'named_colors' in self.machine.config:
            self._load_named_colors()

    def _update_brightness(self, *args):
        """Update brightness factor."""
        del args
        self.brightness_factor, future = self._brightness_template.evaluate_and_subscribe([])
        future.add_done_callback(self._update_brightness)

    def _load_named_colors(self):
        """Load named colors from config."""
        for name, color in self.machine.config['named_colors'].items():
            RGBColor.add_color(name, color)

    def initialise_light_subsystem(self):
        """Initialise the light subsystem."""
        if self._initialised:
            return
        self._initialised = True
        self.machine.validate_machine_config_section('light_settings')

        if self.machine.config['light_settings']['color_correction_profiles'] is None:
            self.machine.config['light_settings']['color_correction_profiles'] = (
                dict())

        # Create the default color correction profile and add it to the machine
        default_profile = RGBColorCorrectionProfile.default()
        self.light_color_correction_profiles['default'] = default_profile

        # Add any user-defined profiles specified in the machine config file
        for profile_name, profile_parameters in (
                self.machine.config['light_settings']
                ['color_correction_profiles'].items()):
            self.machine.config_validator.validate_config(
                'color_correction_profile',
                self.machine.config['light_settings']['color_correction_profiles']
                [profile_name], profile_parameters)

            profile = RGBColorCorrectionProfile(profile_name)
            profile.generate_from_parameters(
                gamma=profile_parameters['gamma'],
                whitepoint=profile_parameters['whitepoint'],
                linear_slope=profile_parameters['linear_slope'],
                linear_cutoff=profile_parameters['linear_cutoff'])
            self.light_color_correction_profiles[profile_name] = profile

        # add setting for brightness
        self.machine.settings.add_setting(SettingEntry("brightness", "Brightness", 100, "brightness", 1.0,
                                                       {0.25: "25%", 0.5: "50%", 0.75: "75%", 1.0: "100% (default)"},
                                                       "standard"))

    def monitor_lights(self):
        """Update the color of lights for the monitor."""
        if not self._monitor_update_task:
            self._monitor_update_task = self.machine.clock.loop.create_task(self._monitor_update_lights())
            self._monitor_update_task.add_done_callback(Util.raise_exceptions)

    async def _monitor_update_lights(self):
        colors = {}
        while True:
            for light in self.machine.lights.values():
                color = light.get_color()
                old = colors.get(light, None)
                if old != color:
                    self.machine.device_manager.notify_device_changes(light, "color", old, color)
                    colors[light] = color
            await asyncio.sleep(1 / self.machine.config['mpf']['default_light_hw_update_hz'])
