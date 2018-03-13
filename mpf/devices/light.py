"""Contains the Light class."""
from functools import partial
from operator import itemgetter

from typing import Set, Dict, List, Tuple, Any

from mpf.core.delays import DelayManager

from mpf.core.platform import LightsPlatform

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.system_wide_device import SystemWideDevice
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade
from mpf.devices.device_mixins import DevicePositionMixin


class DriverLight(LightPlatformSoftwareFade):

    """A coil which is used to drive a light."""

    def __init__(self, driver, loop, software_fade_ms):
        """Initialise coil as light."""
        super().__init__(driver.hw_driver.number, loop, software_fade_ms)
        self.driver = driver

    def set_brightness(self, brightness: float):
        """Set pwm to coil."""
        if brightness <= 0:
            self.driver.disable()
        else:
            self.driver.enable(hold_power=brightness)

    def get_board_name(self):
        """Return board name of underlaying driver."""
        return self.driver.hw_driver.get_board_name()


@DeviceMonitor(_color="color")
class Light(SystemWideDevice, DevicePositionMixin):

    """A light in a pinball machine."""

    config_section = 'lights'
    collection = 'lights'
    class_label = 'light'

    def __init__(self, machine, name):
        """Initialise light."""
        self.hw_drivers = {}
        self.platforms = set()      # type: Set[LightsPlatform]
        super().__init__(machine, name)
        self.machine.light_controller.initialise_light_subsystem()
        self.delay = DelayManager(self.machine.delayRegistry)

        self.default_fade_ms = None

        self._color_correction_profile = None

        self.stack = list()
        """A list of dicts which represents different commands that have come
        in to set this light to a certain color (and/or fade). Each entry in the
        list contains the following key/value pairs:

        priority:
            The relative priority of this color command. Higher numbers
            take precedent, and the highest priority entry will be the command
            that's currently active. In the event of a tie, whichever entry was
            added last wins (based on 'start_time' below).
        start_time:
            The clock time when this command was added. Primarily used
            to calculate fades, but also used as a tie-breaker for multiple
            entries with the same priority.
        start_color:
            RGBColor() of the color of this light when this command came in.
        dest_time:
            Clock time that represents when a fade (from start_color to
            dest_color) will be done. If this is 0, that means there is no
            fade. When a fade is complete, this value is reset to 0.
        dest_color:
            RGBColor() of the destination this light is fading to. If
            a command comes in with no fade, then this will be the same as the
            'color' below.
        key:
            An arbitrary unique identifier to keep multiple entries in the
            stack separate. If a new color command comes in with a key that
            already exists for an entry in the stack, that entry will be
            replaced by the new entry. The key is also used to remove entries
            from the stack (e.g. when shows or modes end and they want to
            remove their commands from the light).
        """

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Register handler for duplicate light number checks."""
        machine.events.add_handler("init_phase_4",
                                   cls._check_duplicate_light_numbers,
                                   machine=machine)

    def get_hw_numbers(self):
        """Return a list of all hardware driver numbers."""
        numbers = []
        for _, drivers in sorted(self.hw_drivers.items()):
            for driver in sorted(drivers, key=lambda x: x.number):
                numbers.append(driver.number)

        return numbers

    @staticmethod
    def _check_duplicate_light_numbers(machine, **kwargs):
        del kwargs
        check_set = set()
        for light in machine.lights:
            for drivers in light.hw_drivers.values():
                for driver in drivers:
                    key = (light.platform, driver.number, type(driver))
                    if key in check_set:
                        raise AssertionError(
                            "Duplicate light number {} {} for light {}".format(
                                type(driver), driver.number, light))

                    check_set.add(key)

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

        channels = {}   # type: Dict[str, List[Any]]
        for color_name in color_channels:
            # red channel
            if color_name == 'r':
                full_color_name = "red"
            # green channel
            elif color_name == 'g':
                full_color_name = "green"
            # blue channel
            elif color_name == 'b':
                full_color_name = "blue"
            # simple white channel
            elif color_name == 'w':
                full_color_name = "white"
            else:
                raise AssertionError("Invalid element {} in type {} of light {}".format(
                    color_name, self.config['type'], self.name))

            if full_color_name not in channels:
                channels[full_color_name] = []
            channels[full_color_name].append(channel_list.pop(0))

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
            try:
                channel_list = platform.parse_light_number_to_channels(self.config['number'], self.config['subtype'])
            except AssertionError as e:
                raise AssertionError("Failed to parse light number {} in platform. See error above".
                                     format(self.name)) from e

            # copy platform and platform_settings to all channels
            for channel, _ in enumerate(channel_list):
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
            # ensure that we got lists
            for channel in channels:
                if not isinstance(channels[channel], list):
                    channels[channel] = [channels[channel]]

        if not channels:
            raise AssertionError("Light {} has no channels.".format(self.name))

        for color, channel_list in channels.items():
            self.hw_drivers[color] = []
            for channel in channel_list:
                channel = self.machine.config_validator.validate_config("light_channels", channel)
                self.hw_drivers[color].append(self._load_hw_driver(channel))

    def _load_hw_driver(self, channel):
        """Load one channel."""
        if channel['platform'] == "drivers":
            return DriverLight(self.machine.coils[channel['number'].strip()], self.machine.clock.loop,
                               int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000))
        else:
            platform = self.machine.get_platform_sections('lights', channel['platform'])
            self.platforms.add(platform)
            try:
                return platform.configure_light(channel['number'], channel['subtype'], channel['platform_settings'])
            except AssertionError as e:
                raise AssertionError("Failed to configure light {} in platform. See error above".
                                     format(self.name)) from e

    def _initialize(self):
        self._load_hw_drivers()

        self.config['default_on_color'] = RGBColor(self.config['default_on_color'])

        if self.config['color_correction_profile'] is not None:
            profile_name = self.config['color_correction_profile']
        elif 'light_settings' in self.machine.config and \
                self.machine.config['light_settings']['default_color_correction_profile'] is not None:
            profile_name = self.machine.config['light_settings']['default_color_correction_profile']
        else:
            profile_name = None

        if profile_name:
            if profile_name in self.machine.light_controller.light_color_correction_profiles:
                profile = self.machine.light_controller.light_color_correction_profiles[profile_name]

                if profile is not None:
                    self._set_color_correction_profile(profile)
            else:   # pragma: no cover
                error = "Color correction profile '{}' was specified for light '{}'"\
                        " but the color correction profile does not exist."\
                        .format(profile_name, self.name)
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

    def _set_color_correction_profile(self, profile):
        """Apply a color correction profile to this light.

        Args:
            profile: An RGBColorCorrectionProfile() instance

        """
        self._color_correction_profile = profile

    def color(self, color, fade_ms=None, priority=0, key=None):
        """Add or update a color entry in this light's stack.

        Calling this methods is how you tell this light what color you want it to be.

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
        """
        self.debug_log("Received color() command. color: %s, fade_ms: %s"
                       "priority: %s, key: %s", color, fade_ms, priority,
                       key)

        if isinstance(color, str) and color == "on":
            color = self.config['default_on_color']
        elif not isinstance(color, RGBColor):
            color = RGBColor(color)

        if fade_ms is None:
            fade_ms = self.default_fade_ms

        start_time = self.machine.clock.get_time()

        color_changes = not self.stack or self.stack[0]['priority'] <= priority or self.stack[0]['dest_color'] is None

        self._add_to_stack(color, fade_ms, priority, key, start_time)

        if color_changes:
            self._schedule_update()

    def on(self, brightness=None, fade_ms=None, priority=0, key=None, **kwargs):
        """Turn light on.

        Args:
            key: key for removal later on
            priority: priority on stack
            fade_ms: duration of fade
        """
        del kwargs
        color = self.config['default_on_color']
        if brightness is not None:
            color *= brightness / 255
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

    # pylint: disable-msg=too-many-arguments
    def _add_to_stack(self, color, fade_ms, priority, key, start_time):
        """Add color to stack."""
        # handle None to make keys sortable
        if not key:
            key = ""
        else:
            key = str(key)

        if priority < self._get_priority_from_key(key):
            self.debug_log("Incoming priority %s is lower than an existing "
                           "stack item with the same key %s. Not adding to "
                           "stack.", priority, key)
            return

        if self.stack and priority == self.stack[0]['priority'] and key == self.stack[0]['key']:
            self.debug_log("Light stack contains two entries with the same priority %s but different keys: ",
                           priority, self.stack)

        if fade_ms:
            dest_time = start_time + (fade_ms / 1000)
        else:
            dest_time = 0

        color_below = self.get_color_below(priority, key)
        self._remove_from_stack_by_key(key)

        self.stack.append(dict(priority=priority,
                               start_time=start_time,
                               start_color=color_below,
                               dest_time=dest_time,
                               dest_color=color,
                               key=key))

        self.stack.sort(key=itemgetter('priority', 'key'), reverse=True)

        self.debug_log("+-------------- Adding to stack ----------------+")
        self.debug_log("priority: %s", priority)
        self.debug_log("start_time: %s", self.machine.clock.get_time())
        self.debug_log("start_color: %s", color_below)
        self.debug_log("dest_time: %s", dest_time)
        self.debug_log("dest_color: %s", color)
        self.debug_log("key: %s", key)

    def remove_from_stack_by_key(self, key, fade_ms=None):
        """Remove a group of color settings from the stack.

        Args:
            key: The key of the settings to remove (based on the 'key'
                parameter that was originally passed to the color() method.)

        This method triggers a light update, so if the highest priority settings
        were removed, the light will be updated with whatever's below it. If no
        settings remain after these are removed, the light will turn off.
        """
        if not self.stack:
            # no stack
            return

        if fade_ms is None:
            fade_ms = self.default_fade_ms

        key = str(key)

        priority = None
        color_changes = True
        stack = []
        for i, entry in enumerate(self.stack):
            if entry["key"] == key:
                stack = self.stack[i:]
                priority = entry["priority"]
                break
            elif entry["dest_color"] is not None:
                # no transparency above key
                color_changes = False

        # key not in stack
        if not stack:
            return

        # this is already a fadeout. do not fade out the fade out.
        if stack[0]["dest_color"] is None:
            fade_ms = None

        if fade_ms:
            color_of_key = self._get_color_and_fade(stack, 0)[0]

        self._remove_from_stack_by_key(key)
        if fade_ms:
            start_time = self.machine.clock.get_time()
            self.stack.append(dict(priority=priority,
                                   start_time=start_time,
                                   start_color=color_of_key,
                                   dest_time=start_time + fade_ms / 1000.0,
                                   dest_color=None,
                                   key=key))
            self.delay.reset(ms=fade_ms, callback=partial(self._remove_fade_out, key=key), name="remove_fade")
            self.stack.sort(key=itemgetter('priority', 'key'), reverse=True)

        if color_changes:
            self._schedule_update()

    def _remove_fade_out(self, key):
        """Remove a timed out fade out."""
        if not self.stack:
            return

        found = False
        color_change = True
        for _, entry in enumerate(self.stack):
            if entry["key"] == key and entry["dest_color"] is None:
                found = True
                break
            elif entry["dest_color"] is not None:
                # found entry above the removed which is non-transparent
                color_change = False

        if found:
            self.debug_log("Removing fadeout for key '%s' from stack", key)
            self.stack[:] = [x for x in self.stack if x['key'] != key or x['dest_color'] is not None]

        if found and color_change:
            self._schedule_update()

    def _remove_from_stack_by_key(self, key):
        """Remove a key from stack."""
        # tune the common case
        if not self.stack:
            return
        self.debug_log("Removing key '%s' from stack", key)
        self.stack[:] = [x for x in self.stack if x['key'] != key]

    def _schedule_update(self):
        for color, hw_drivers in self.hw_drivers.items():
            for hw_driver in hw_drivers:
                hw_driver.set_fade(partial(self._get_brightness_and_fade, color=color))

        for platform in self.platforms:
            platform.light_sync()

    def clear_stack(self):
        """Remove all entries from the stack and resets this light to 'off'."""
        self.stack[:] = []

        self.debug_log("Clearing Stack")

        self._schedule_update()

    def _get_priority_from_key(self, key):
        try:
            return [x for x in self.stack if x['key'] == key][0]['priority']
        except IndexError:
            return 0

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

    # pylint: disable-msg=too-many-return-statements
    def _get_color_and_fade(self, stack, max_fade_ms: int) -> Tuple[RGBColor, int]:
        try:
            color_settings = stack[0]
        except IndexError:
            # no stack
            return RGBColor('off'), -1

        dest_color = color_settings['dest_color']

        # no fade
        if not color_settings['dest_time']:
            # if we are transparent just return the lower layer
            if dest_color is None:
                return self._get_color_and_fade(stack[1:], max_fade_ms)
            return dest_color, -1

        current_time = self.machine.clock.get_time()

        # fade is done
        if current_time >= color_settings['dest_time']:
            # if we are transparent just return the lower layer
            if dest_color is None:
                return self._get_color_and_fade(stack[1:], max_fade_ms)
            return color_settings['dest_color'], -1

        if dest_color is None:
            dest_color, lower_fade_ms = self._get_color_and_fade(stack[1:], max_fade_ms)
            if lower_fade_ms > 0:
                max_fade_ms = lower_fade_ms

        target_time = current_time + (max_fade_ms / 1000.0)
        # check if fade will be done before max_fade_ms
        if target_time > color_settings['dest_time']:
            return dest_color, int((color_settings['dest_time'] - current_time) * 1000)

        # figure out the ratio of how far along we are
        try:
            ratio = ((target_time - color_settings['start_time']) /
                     (color_settings['dest_time'] - color_settings['start_time']))
        except ZeroDivisionError:
            ratio = 1.0

        return RGBColor.blend(color_settings['start_color'], dest_color, ratio), max_fade_ms

    def _get_brightness_and_fade(self, max_fade_ms: int, color: str) -> Tuple[float, int]:
        uncorrected_color, fade_ms = self._get_color_and_fade(self.stack, max_fade_ms)
        corrected_color = self.gamma_correct(uncorrected_color)
        corrected_color = self.color_correct(corrected_color)

        if color in ["red", "blue", "green"]:
            brightness = getattr(corrected_color, color) / 255.0
        elif color == "white":
            brightness = min(corrected_color.red, corrected_color.green, corrected_color.blue) / 255.0
        else:
            raise ColorException("Invalid color {}".format(color))
        return brightness, fade_ms

    @property
    def _color(self):
        """Getter for color."""
        return self.get_color()

    def get_color_below(self, priority, key):
        """Return an RGBColor() instance of the 'color' setting of the highest color below a certain key.

        Similar to get_color.
        """
        if not self.stack:
            return RGBColor("off")

        stack = []
        for i, entry in enumerate(self.stack):
            if entry['priority'] <= priority and entry["key"] <= key:
                stack = self.stack[i:]
                break
        return self._get_color_and_fade(stack, 0)[0]

    def get_color(self):
        """Return an RGBColor() instance of the 'color' setting of the highest color setting in the stack.

        This is usually the same color as the physical light, but not always (since physical lights are updated once per
        frame, this value could vary.

        Also note the color returned is the "raw" color that does has not had the color correction profile applied.
        """
        return self._get_color_and_fade(self.stack, 0)[0]

    @property
    def fade_in_progress(self) -> bool:
        """Return true if a fade is in progress."""
        return bool(self.stack and self.stack[0]['dest_time'] > self.machine.clock.get_time())
