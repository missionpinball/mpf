"""Handles all light updates."""
from mpf.core.settings_controller import SettingEntry

from mpf.core.rgb_color import RGBColorCorrectionProfile

from mpf.core.mpf_controller import MpfController


class LightController(MpfController):

    """Handles light updates."""

    def __init__(self, machine):
        """Initialise lights controller."""
        super().__init__(machine)

        # Generate and add color correction profiles to the machine
        self.light_color_correction_profiles = dict()

        self.lights_to_update = set()
        self._initialised = False
        self._updater_task = None

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

        # schedule the single machine-wide update to write the current light of
        # each light to the hardware
        self._updater_task = self.machine.clock.schedule_interval(
            self._update_lights, 1 / self.machine.config['mpf']['default_light_hw_update_hz'])

        self.machine.settings.add_setting(SettingEntry("brightness", "Brightness", 100, "brightness", 1.0,
                                                       {0.25: "25%", 0.5: "50%", 0.75: "75%", 1.0: "100% (default)"}))

    def _update_lights(self, dt):
        """Write lights to hardware platform.

        Called periodically (default at the end of every frame) to write the
        new light colors to the hardware for the lights that changed during that
        frame.

        Args:
            dt: time since last call
        """
        del dt

        new_lights_to_update = set()
        if self.lights_to_update:
            for light in self.lights_to_update:
                light.write_color_to_hw_driver()
                if light.fade_in_progress:
                    new_lights_to_update.add(light)
            self.lights_to_update = new_lights_to_update
