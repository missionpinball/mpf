"""Contains the Light class."""
from operator import itemgetter

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.rgb_color import RGBColor
from mpf.core.rgb_color import RGBColorCorrectionProfile
from mpf.core.settings_controller import SettingEntry
from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.driver import ReconfiguredDriver
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class DriverLight(LightPlatformInterface):

    """A coil which is used to drive a light."""

    def __init__(self, driver):
        """Initialise coil as light."""
        self.driver = driver

    def set_brightness(self, brightness: float, fade_ms: int):
        """Set pwm to coil."""
        # TODO: fix driver interface
        if brightness <= 0:
            self.driver.disable()
        else:
            driver = ReconfiguredDriver(self.driver, {"hold_power": 8 * brightness})
            driver.enable()


@DeviceMonitor(_color="color", _corrected_color="corrected_color")
class Light(SystemWideDevice):

    """A light in a pinball machine."""

    config_section = 'lights'
    collection = 'lights'
    class_label = 'light'
    machine = None

    lights_to_update = set()
    lights_to_fade = set()
    _updater_task = None

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Initialise all lights.

        Args:
            machine: MachineController which is used
        """
        cls.machine = machine
        cls.lights_to_fade = set()
        cls.lights_to_update = set()

        machine.validate_machine_config_section('light_settings')

        if machine.config['light_settings']['color_correction_profiles'] is None:
            machine.config['light_settings']['color_correction_profiles'] = (
                dict())

        # Generate and add color correction profiles to the machine
        cls.light_color_correction_profiles = dict()

        # Create the default color correction profile and add it to the machine
        default_profile = RGBColorCorrectionProfile.default()
        cls.light_color_correction_profiles['default'] = default_profile

        # Add any user-defined profiles specified in the machine config file
        for profile_name, profile_parameters in (
                machine.config['light_settings']
                ['color_correction_profiles'].items()):

            machine.config_validator.validate_config(
                'color_correction_profile',
                machine.config['light_settings']['color_correction_profiles']
                [profile_name], profile_parameters)

            profile = RGBColorCorrectionProfile(profile_name)
            profile.generate_from_parameters(
                gamma=profile_parameters['gamma'],
                whitepoint=profile_parameters['whitepoint'],
                linear_slope=profile_parameters['linear_slope'],
                linear_cutoff=profile_parameters['linear_cutoff'])
            cls.light_color_correction_profiles[profile_name] = profile

        # schedule the single machine-wide update to write the current light of
        # each light to the hardware
        cls._updater_task = machine.clock.schedule_interval(
            cls.update_lights, 1 / machine.config['mpf']['default_light_hw_update_hz'])

        machine.mode_controller.register_stop_method(cls.mode_stop)

        machine.settings.add_setting(SettingEntry("brightness", "Brightness", 100, "brightness", 1.0,
                                                  {0.25: "25%", 0.5: "50%", 0.75: "75%", 1.0: "100% (default)"}))

    @classmethod
    def update_lights(cls, dt):
        """Write lights to hardware platform.

        Called periodically (default at the end of every frame) to write the
        new light colors to the hardware for the lights that changed during that
        frame.

        Args:
            dt: time since last call
        """
        for light in list(cls.lights_to_fade):
            if light.fade_in_progress:
                light.fade_task(dt)

        # todo we could make a change here (or an option) so that it writes
        # every light, every frame. That way they'd fix themselves if something
        # got weird due to interference? Or is that a platform thing?

        if cls.lights_to_update:
            for light in cls.lights_to_update:
                light.write_color_to_hw_driver()

            cls.lights_to_update = set()

    @classmethod
    def mode_stop(cls, mode: Mode):
        """Remove all entries from mode.

        Args:
            mode: Mode which was removed
        """
        for light in cls.machine.lights:
            light.remove_from_stack_by_mode(mode)

    def __init__(self, machine, name):
        """Initialise light."""
        self.hw_drivers = {}
        self._color = [0, 0, 0]
        self._corrected_color = [0, 0, 0]
        super().__init__(machine, name)

        self.fade_in_progress = False
        self.default_fade_ms = None

        self._color_correction_profile = None

        self.stack = list()
        """A list of dicts which represents different commands that have come
        in to set this light to a certain color (and/or fade). Each entry in the
        list contains the following key/value pairs:

        priority: The relative priority of this color command. Higher numbers
            take precedent, and the highest priority entry will be the command
            that's currently active. In the event of a tie, whichever entry was
            added last wins (based on 'start_time' below).
        start_time: The clock time when this command was added. Primarily used
            to calculate fades, but also used as a tie-breaker for multiple
            entries with the same priority.
        start_color: RGBColor() of the color of this light when this command came
            in.
        dest_time: Clock time that represents when a fade (from start_color to
            dest_color) will be done. If this is 0, that means there is no
            fade. When a fade is complete, this value is reset to 0.
        dest_color: RGBColor() of the destination this light is fading to. If
            a command comes in with no fade, then this will be the same as the
            'color' below.
        color: The current color of the light based on this command. This value
            is updated automatically as fades progress, and it's the value
            that's actually written to the hardware (prior to color
            correction).
        key: An arbitrary unique identifier to keep multiple entries in the
            stack separate. If a new color command comes in with a key that
            already exists for an entry in the stack, that entry will be
            replaced by the new entry. The key is also used to remove entries
            from the stack (e.g. when shows or modes end and they want to
            remove their commands from the light).
        mode: Optional mode where the brightness was set. Used to remove
            entries when a mode ends.
        """

    def _map_channels_to_colors(self, channel_list) -> dict:
        if self.config['type']:
            color_channels = self.config['type']
        else:
            if len(channel_list) == 1:
                # for one channel default to a white channel
                color_channels = "w"
            elif len(channel_list) == 3:
                # for three channels default to RGB
                color_channels = "rgb"
            else:
                raise AssertionError("Please provide a type for light {}. No default for channels {}.".
                                     format(self.name, channel_list))

        if len(channel_list) != len(color_channels):
            raise AssertionError("Type {} does not match channels {} for light {}".format(
                color_channels, channel_list, self.name
            ))

        channels = {}
        for color_name in color_channels:
            # red channel
            if color_name == 'r':
                channels["red"] = channel_list.pop(0)
            # green channel
            elif color_name == 'g':
                channels["green"] = channel_list.pop(0)
            # blue channel
            elif color_name == 'b':
                channels["blue"] = channel_list.pop(0)
            # simple white channel
            elif color_name == 'w':
                channels["white"] = channel_list.pop(0)
            else:
                raise AssertionError("Invalid element {} in type {} of light {}".format(
                    color_name, self.config['type'], self.name))

        return channels

    def _load_hw_drivers(self):
        """Load hw drivers."""
        if self.config['platform'] == "drivers":
            channel_list = [
                {
                    "number": self.config['number'],
                    "platform": "drivers"
                }
            ]
            # map channel to color
            channels = self._map_channels_to_colors(channel_list)
        elif not self.config['channels']:
            # get channels from number + platform
            platform = self.machine.get_platform_sections('lights', self.config['platform'])
            channel_list = platform.parse_light_number_to_channels(self.config['number'], self.config['subtype'])
            # copy platform and platform_settings to all channels
            for channel, settings in enumerate(channel_list):
                channel_list[channel]['subtype'] = self.config['subtype']
                channel_list[channel]['platform'] = self.config['platform']
                channel_list[channel]['platform_settings'] = self.config['platform_settings']
            # map channels to colors
            channels = self._map_channels_to_colors(channel_list)
        else:
            if self.config['number'] or self.config['platform'] or self.config['platform_settings']:
                raise AssertionError("Light {} cannot contain platform/platform_settings/number and channels".
                                     format(self.name))
            # alternatively use channels from config
            channels = self.config['channels']

        if not channels:
            raise AssertionError("Light {} has no channels.".format(self.name))

        for num, channel in channels.items():
            channel = self.machine.config_validator.validate_config("light_channels", channel)
            self.hw_drivers[num] = self._load_hw_driver(channel)

    def _load_hw_driver(self, channel):
        """Load one channel."""
        if channel['platform'] == "drivers":
            return DriverLight(self.machine.coils[channel['number'].strip()])
        else:
            platform = self.machine.get_platform_sections('lights', channel['platform'])
            return platform.configure_light(channel['number'], channel['subtype'], channel['platform_settings'])

    def _initialize(self):
        self._load_hw_drivers()

        self.config['default_on_color'] = RGBColor(self.config['default_on_color'])

        if self.config['color_correction_profile'] is not None:
            if self.config['color_correction_profile'] in (
                    self.light_color_correction_profiles):
                profile = self.light_color_correction_profiles[
                    self.config['color_correction_profile']]

                if profile is not None:
                    self.set_color_correction_profile(profile)
            else:   # pragma: no cover
                error = "Color correction profile '{}' was specified for light '{}'"\
                        " but the color correction profile does not exist."\
                    .format(self.config['color_correction_profile'], self.name)
                self.error_log(error)
                raise ValueError(error)

        if self.config['fade_ms'] is not None:
            self.default_fade_ms = self.config['fade_ms']
        else:
            self.default_fade_ms = (self.machine.config['light_settings']
                                    ['default_fade_ms'])

        self.debug_log("Initializing Light. CC Profile: %s, "
                       "Default fade: %sms", self._color_correction_profile,
                       self.default_fade_ms)

    def set_color_correction_profile(self, profile):
        """Apply a color correction profile to this light.

        Args:
            profile: An RGBColorCorrectionProfile() instance

        """
        self._color_correction_profile = profile

    # pylint: disable-msg=too-many-arguments
    def color(self, color, fade_ms=None, priority=0, key=None, mode=None):
        """Add or update a color entry in this light's stack, which is how you tell this light what color you want it to be.

        Args:
            color: RGBColor() instance, or a string color name, hex value, or
                3-integer list/tuple of colors.
            fade_ms: Int of the number of ms you want this light to fade to the
                color in. A value of 0 means it's instant. A value of None (the
                default) means that it will use this light's and/or the machine's
                default fade_ms setting.
            priority: Int value of the priority of these incoming settings. If
                this light has current settings in the stack at a higher
                priority, the settings you're adding here won't take effect.
                However they're still added to the stack, so if the higher
                priority settings are removed, then the next-highest apply.
            key: An arbitrary identifier (can be any immutable object) that's
                used to identify these settings for later removal. If any
                settings in the stack already have this key, those settings
                will be replaced with these new settings.
            mode: Optional mode instance of the mode that is setting this
                color. When a mode ends, entries from the stack with that mode
                will automatically be removed.
        """
        self.debug_log("Received color() command. color: %s, fade_ms: %s"
                       "priority: %s, key: %s", color, fade_ms, priority,
                       key)

        if not isinstance(color, RGBColor):
            color = RGBColor(color)

        if fade_ms is None:
            fade_ms = self.default_fade_ms

        if priority < self._get_priority_from_key(key):
            self.debug_log("Incoming priority is lower than an existing "
                           "stack item with the same key. Not adding to "
                           "stack.")

            return

        self._add_to_stack(color, fade_ms, priority, key, mode)

    # pylint: disable-msg=too-many-arguments
    def _add_to_stack(self, color, fade_ms, priority, key, mode):
        curr_color = self.get_color()

        self.remove_from_stack_by_key(key)

        if fade_ms:
            new_color = curr_color
            dest_time = self.machine.clock.get_time() + (fade_ms / 1000)
        else:
            new_color = color
            dest_time = 0

        self.stack.append(dict(priority=priority,
                               start_time=self.machine.clock.get_time(),
                               start_color=curr_color,
                               dest_time=dest_time,
                               dest_color=color,
                               color=new_color,
                               key=key,
                               mode=mode))

        self.stack.sort(key=itemgetter('priority', 'start_time'), reverse=True)

        self.debug_log("+-------------- Adding to stack ----------------+")
        self.debug_log("priority: %s", priority)
        self.debug_log("start_time: %s", self.machine.clock.get_time())
        self.debug_log("start_color: %s", curr_color)
        self.debug_log("dest_time: %s", dest_time)
        self.debug_log("dest_color: %s", color)
        self.debug_log("color: %s", new_color)
        self.debug_log("key: %s", key)

        self.__class__.lights_to_update.add(self)

    def clear_stack(self):
        """Remove all entries from the stack and resets this light to 'off'."""
        self.stack[:] = []

        self.debug_log("Clearing Stack")

        self.__class__.lights_to_update.add(self)

    def remove_from_stack_by_key(self, key):
        """Remove a group of color settings from the stack.

        Args:
            key: The key of the settings to remove (based on the 'key'
                parameter that was originally passed to the color() method.)

        This method triggers a light update, so if the highest priority settings
        were removed, the light will be updated with whatever's below it. If no
        settings remain after these are removed, the light will turn off.
        """
        self.debug_log("Removing key '%s' from stack", key)

        self.stack[:] = [x for x in self.stack if x['key'] != key]
        self.__class__.lights_to_update.add(self)

    def remove_from_stack_by_mode(self, mode: Mode):
        """Remove a group of color settings from the stack.

        Args:
            mode: Mode which was removed

        This method triggers a light update, so if the highest priority settings
        were removed, the light will be updated with whatever's below it. If no
        settings remain after these are removed, the light will turn off.
        """
        self.debug_log("Removing mode '%s' from stack", mode)

        self.stack[:] = [x for x in self.stack if x['mode'] != mode]
        self.__class__.lights_to_update.add(self)

    def get_color(self):
        """Return an RGBColor() instance of the 'color' setting of the highest color setting in the stack.

        This is usually the same color as the
        physical light, but not always (since physical lights are updated once per
        frame, this value could vary.

        Also note the color returned is the "raw" color that does has not had
        the color correction profile applied.
        """
        try:
            return self.stack[0]['color']
        except IndexError:
            return RGBColor('off')

    def _get_priority_from_key(self, key):
        try:
            return [x for x in self.stack if x['key'] == key][0]['priority']
        except IndexError:
            return 0

    def write_color_to_hw_driver(self):
        """Set color to hardware platform.

        Physically update the light hardware object based on the 'color'
        setting of the highest priority setting from the stack.

        This method is automatically called whenever a color change has been
        made (including when fades are active).
        """
        # TODO: untangle fade and setting values. remove delay?
        if not self.stack:
            self.color('off')

        # if there's a current fade, but the new command doesn't have one
        if not self.stack[0]['dest_time'] and self.fade_in_progress:
            self._stop_fade_task()

        # If the new command has a fade, but the fade task isn't running
        if self.stack[0]['dest_time'] and not self.fade_in_progress:
            self._setup_fade()

        # If there's no current fade and no new fade, or a current fade and new
        # fade
        else:
            corrected_color = self.gamma_correct(self.stack[0]['color'])
            corrected_color = self.color_correct(corrected_color)

            self._color = list(self.stack[0]['color'])
            self._corrected_color = corrected_color
            self.debug_log("Writing color to hw driver: %s", corrected_color)

            for color, hw_driver in self.hw_drivers.items():
                # TODO: implement fade_ms here
                fade_ms = 0
                if color in ["red", "blue", "green"]:
                    hw_driver.set_brightness(getattr(corrected_color, color) / 255.0, fade_ms)
                elif color == "white":
                    hw_driver.set_brightness(
                        min(corrected_color.red, corrected_color.green, corrected_color.blue) / 255.0, fade_ms)
                else:
                    raise AssertionError("Invalid color {} in light {}".format(color, self.name))

    def gamma_correct(self, color):
        """Apply max brightness correction to color.

        Args:
            color: The RGBColor() instance you want to have gamma applied.

        Returns:
            An updated RGBColor() instance with gamma corrected.
        """
        factor = self.machine.get_machine_var("brightness")
        if not factor:
            return color
        else:
            return RGBColor([int(x * factor) for x in color])

    def color_correct(self, color):
        """Apply the current color correction profile to the color passed.

        Args:
            color: The RGBColor() instance you want to get color corrected.

        Returns:
            An updated RGBColor() instance with the current color correction
            profile applied.

        Note that if there is no current color correction profile applied, the
        returned color will be the same as the color that was passed.
        """
        if self._color_correction_profile is None:
            return color
        else:

            self.debug_log("Applying color correction: %s (applied "
                           "'%s' color correction profile)",
                           self._color_correction_profile.apply(color),
                           self._color_correction_profile.name)

            return self._color_correction_profile.apply(color)

    def on(self, fade_ms=None, brightness=None, priority=0, key=None, **kwargs):
        """Turn light on.

        Args:
            key: key for removal later on
            priority: priority on stack
            fade_ms: duration of fade
        """
        del kwargs
        if brightness is not None:
            color = (brightness, brightness, brightness)
        else:
            color = self.config['default_on_color']
        self.color(color=color, fade_ms=fade_ms,
                   priority=priority, key=key)

    def off(self, fade_ms=None, priority=0, key=None, **kwargs):
        """Turn light off.

        Args:
            key: key for removal later on
            priority: priority on stack
            fade_ms: duration of fade
        """
        del kwargs
        self.color(color=RGBColor(), fade_ms=fade_ms, priority=priority,
                   key=key)

    def _setup_fade(self):
        self.fade_in_progress = True

        self.debug_log("Setting up the fade task")

        self.__class__.lights_to_fade.add(self)

    def fade_task(self, dt):
        """Perform a fade depending on the current time.

        Args:
            dt: time since last call
        """
        del dt

        try:
            color_settings = self.stack[0]
        except IndexError:
            self._stop_fade_task()
            return

        # todo
        if not color_settings['dest_time']:
            return

        # figure out the ratio of how far along we are
        try:
            ratio = ((self.machine.clock.get_time() -
                      color_settings['start_time']) /
                     (color_settings['dest_time'] -
                      color_settings['start_time']))
        except ZeroDivisionError:
            ratio = 1.0

        self.debug_log("Fade task, ratio: %s", ratio)

        if ratio >= 1.0:  # fade is done
            self._end_fade()
            color_settings['color'] = color_settings['dest_color']
        else:
            color_settings['color'] = (
                RGBColor.blend(color_settings['start_color'],
                               color_settings['dest_color'],
                               ratio))

        self.__class__.lights_to_update.add(self)

    def _end_fade(self):
        # stops the fade and instantly sets the light to its destination color
        self._stop_fade_task()
        self.stack[0]['dest_time'] = 0

    def _stop_fade_task(self):
        # stops the fade task. Light is left in whatever state it was in
        self.fade_in_progress = False
        self.__class__.lights_to_fade.remove(self)

        self.debug_log("Stopping fade task")
