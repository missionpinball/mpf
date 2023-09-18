"""Contains the Light class."""
import asyncio

from functools import partial

from typing import Set, Dict, List, Tuple, Any

from mpf.core.delays import DelayManager

from mpf.core.platform import LightsPlatform, LightConfig, LightConfigColors

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.device_mixins import DevicePositionMixin
from mpf.exceptions.config_file_error import ConfigFileError

MYPY = False
if MYPY:
    from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa


class LightStackEntry:

    """Data class for a light stack entry."""

    __slots__ = ["priority", "start_time", "start_color", "dest_time", "dest_color", "key"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, priority, key, start_time, start_color, dest_time, dest_color):
        """Initialize light stack entry."""
        self.priority = priority
        self.key = key
        self.start_time = start_time
        self.start_color = start_color
        self.dest_time = dest_time
        self.dest_color = dest_color

    def __gt__(self, other):
        """Compare two stack entries."""
        return self.priority > other.priority or (self.priority == other.priority and self.key > other.key)

    def __repr__(self):
        """Return string representation."""
        return "<LightStackEntry {}: {} ({}) -> {} ({}) Priority: {}>".format(
            self.key, self.start_color, self.start_time, self.dest_color, self.dest_time, self.priority)


@DeviceMonitor(_color="color", _do_not_overwrite_setter=True)
class Light(SystemWideDevice, DevicePositionMixin):

    """A light in a pinball machine."""

    config_section = 'lights'
    collection = 'lights'
    class_label = 'light'

    __slots__ = ["hw_drivers", "platforms", "delay", "default_fade_ms", "_color_correction_profile", "stack",
                 "_off_color", "_drivers_loaded", "_last_fade_target"]

    def __init__(self, machine, name):
        """initialize light."""
        self.hw_drivers = {}        # type: Dict[str, List[LightPlatformInterface]]
        self.platforms = set()      # type: Set[LightsPlatform]
        super().__init__(machine, name)
        self.machine.light_controller.initialize_light_subsystem()
        self.delay = DelayManager(self.machine)
        self._drivers_loaded = asyncio.Future()

        self.default_fade_ms = None
        self._off_color = RGBColor("off")

        self._color_correction_profile = None
        self._last_fade_target = None

        self.stack = list()     # type: List[LightStackEntry]
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
        for _, drivers in sorted(self.hw_drivers.items(), key=lambda x: x[1]):
            for driver in sorted(drivers, key=lambda x: x.number):
                numbers.append(driver.number)

        return numbers

    @staticmethod
    def _check_duplicate_light_numbers(machine: MachineController, **kwargs):
        del kwargs
        check_set = set()
        for light in machine.lights.values():
            for drivers in light.hw_drivers.values():
                for driver in drivers:
                    key = (light.config['platform'], driver.number, type(driver))
                    if key in check_set:
                        raise ConfigFileError("Duplicate light number {} {} for light {}".format(
                            type(driver), driver.number, light), 10, "light", key, "light")

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
                self.raise_config_error("Please provide a type for light {}. No default for channels {}.".
                                        format(self.name, channel_list), 11)

        if len(channel_list) != len(color_channels):
            self.raise_config_error("Type {} does not match channels {} for light {}".format(
                color_channels, channel_list, self.name), 12)

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
                self.raise_config_error("Invalid element {} in type {} of light {}".format(
                    color_name, self.config['type'], self.name), 13)

            if full_color_name not in channels:
                channels[full_color_name] = []
            channels[full_color_name].append(channel_list.pop(0))

        return channels

    def wait_for_loaded(self):
        """Return future."""
        return asyncio.shield(self._drivers_loaded)

    def get_successor_number(self):
        """Get the number of the next light channel.

        We first have to find the last channel and then get the next number based on that.
        """
        all_drivers = []
        for drivers in self.hw_drivers.values():
            all_drivers.extend(drivers)
        sorted_channels = sorted(all_drivers)
        return sorted_channels[-1].get_successor_number()

    def _load_hw_driver_sequentially(self, next_channel):
        if self.config['number'] or self.config['channels']:
            self.raise_config_error("Cannot use start_channel/previous and number or channels.", 3)
        if not self.config['type']:
            self.raise_config_error("Cannot use previous or start_channel without type. "
                                    "Add a type setting to your light.", 2)

        for color_name in self.config['type']:
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
                self.raise_config_error("Invalid element {} in type {} of light {}".format(
                    color_name, self.config['type'], self.name), 14)

            if full_color_name not in self.hw_drivers:
                self.hw_drivers[full_color_name] = []
            channel = {'subtype': self.config['subtype'], 'platform': self.config['platform'],
                       'platform_settings': self.config['platform_settings'], 'number': next_channel}
            channel = self.machine.config_validator.validate_config("light_channels", channel)
            driver = self._load_hw_driver(channel, full_color_name)
            next_channel = driver.get_successor_number()
            self.hw_drivers[full_color_name].append(driver)

    def _load_hw_drivers(self):
        if not self.config['channels']:
            # get channels from number + platform
            platform = self.machine.get_platform_sections('lights', self.config['platform'])
            platform.assert_has_feature("lights")
            try:
                channel_list = platform.parse_light_number_to_channels(self.config['number'], self.config['subtype'])
            except AssertionError as e:
                self.raise_config_error("Failed to parse light number {} in platform. See error above".
                                        format(self.name), 4, source_exception=e)

            # copy platform and platform_settings to all channels
            for channel, _ in enumerate(channel_list):
                channel_list[channel]['subtype'] = self.config['subtype']
                channel_list[channel]['platform'] = self.config['platform']
                channel_list[channel]['platform_settings'] = self.config['platform_settings']
            # map channels to colors
            channels = self._map_channels_to_colors(channel_list)
        else:
            if self.config['number'] or self.config['platform'] or self.config['platform_settings']:
                self.raise_config_error("Light {} cannot contain platform/platform_settings/number and channels".
                                        format(self.name), 5)
            # alternatively use channels from config
            channels = self.config['channels']
            # ensure that we got lists
            for channel in channels:
                if not isinstance(channels[channel], list):
                    channels[channel] = [channels[channel]]

        if not channels:
            self.raise_config_error("Light {} has no channels.".format(self.name), 6)

        for color, channel_list in channels.items():
            self.hw_drivers[color] = []
            for channel in channel_list:
                channel = self.machine.config_validator.validate_config("light_channels", channel)
                driver = self._load_hw_driver(channel, color)
                self.hw_drivers[color].append(driver)

    def _load_hw_driver(self, channel, color):
        """Load one channel."""
        platform = self.machine.get_platform_sections('lights', channel['platform'])
        self.platforms.add(platform)

        if not platform.features['allow_empty_numbers'] and channel['number'] is None:
            self.raise_config_error("Light must have a number.", 1)

        config = LightConfig(
            name=self.name,
            color=LightConfigColors[color.upper()]
        )

        try:
            return platform.configure_light(channel['number'], channel['subtype'], config, channel['platform_settings'])
        except AssertionError as e:
            self.raise_config_error("Failed to configure light {} in platform. See error above".format(self.name), 7,
                                    source_exception=e)

    async def _initialize(self):
        await super()._initialize()
        try:
            if self.config['previous']:
                if self.config['previous'].name == self.name:
                    self.raise_config_error(
                        "Failed to configure light {} in platform. 'previous' value cannot refer to itself.".
                        format(self.name), 8)

                # If we are in development mode, do a robust tree traversal to catch infinite light loops
                if not self.machine.options['production']:
                    tree = [self.name]
                    prev = self.config['previous']
                    while prev:
                        tree.append(prev.name)
                        prev = prev.config.get('previous')
                        if prev is not None and prev.name in tree:
                            tree.append(prev.name)
                            self.raise_config_error("Cyclical light chain found: {}".format(" -> ".join(tree)), 9)

                await self.config['previous'].wait_for_loaded()
                start_channel = self.config['previous'].get_successor_number()
                self._load_hw_driver_sequentially(start_channel)
            elif self.config['start_channel']:
                self._load_hw_driver_sequentially(self.config['start_channel'])
            else:
                self._load_hw_drivers()
            self._drivers_loaded.set_result(True)

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
        except Exception:
            self._drivers_loaded.cancel()
            raise

    def _set_color_correction_profile(self, profile):
        """Apply a color correction profile to this light.

        Args:
        ----
            profile: An RGBColorCorrectionProfile() instance

        """
        self._color_correction_profile = profile

    # pylint: disable-msg=too-many-arguments
    def color(self, color, fade_ms=None, priority=0, key=None, start_time=None):
        """Add or update a color entry in this light's stack.

        Calling this methods is how you tell this light what color you want it to be.

        Args:
        ----
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
            start_time: Time this occurred to synchronize lights.
        """
        if self._debug:
            self.debug_log("Received color() command. color: %s, fade_ms: %s "
                           "priority: %s, key: %s", color, fade_ms, priority,
                           key)

        if isinstance(color, str) and color == "on":
            color = self.config['default_on_color']
        elif not isinstance(color, RGBColor):
            color = RGBColor(color)

        if fade_ms is None:
            fade_ms = self.default_fade_ms

        if not start_time:
            start_time = self.machine.clock.get_time()

        color_changes = not self.stack or self.stack[0].priority <= priority or self.stack[0].dest_color is None

        self._add_to_stack(color, fade_ms, priority, key, start_time)

        if color_changes:
            self._schedule_update()

    def on(self, brightness=None, fade_ms=None, priority=0, key=None, **kwargs):
        """Turn light on.

        Args:
        ----
            brightness: Brightness factor for "on".
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
        ----
            key: key for removal later on
            priority: priority on stack
            fade_ms: duration of fade
        """
        del kwargs
        self.color(color=self._off_color, fade_ms=fade_ms, priority=priority,
                   key=key)

    # pylint: disable-msg=too-many-arguments
    def _add_to_stack(self, color, fade_ms, priority, key, start_time):
        """Add color to stack."""
        # handle None to make keys sortable
        if key is None:
            key = ""
        elif not isinstance(key, str):
            raise AssertionError("Key should be string")

        if self.stack and priority < self._get_priority_from_key(key):
            if self._debug:
                self.debug_log("Incoming priority %s is lower than an existing "
                               "stack item with the same key %s. Not adding to "
                               "stack.", priority, key)
            return

        if self.stack and self._debug and priority == self.stack[0].priority and key != self.stack[0].key:
            self.debug_log("Light stack contains two entries with the same priority %s but different keys: %s",
                           priority, self.stack)

        if fade_ms:
            dest_time = start_time + (fade_ms / 1000)
            color_below = self.get_color_below(priority, key)
        else:
            dest_time = 0
            color_below = None

        if self.stack:
            self._remove_from_stack_by_key(key)

        self.stack.append(LightStackEntry(priority,
                                          key,
                                          start_time,
                                          color_below,
                                          dest_time,
                                          color))

        if len(self.stack) > 1:
            self.stack.sort(reverse=True)

        if self._debug:
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
        ----
            key: The key of the settings to remove (based on the 'key'
                parameter that was originally passed to the color() method.)
            fade_ms: Time to fade out the light.

        This method triggers a light update, so if the highest priority settings
        were removed, the light will be updated with whatever is below it. If no
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
            if entry.key == key:
                stack = self.stack[i:]
                priority = entry.priority
                break
            if entry.dest_color is not None:
                # no transparency above key
                color_changes = False

        # key not in stack
        if not stack:
            return

        # this is already a fadeout. do not fade out the fade out.
        if stack[0].dest_color is None:
            fade_ms = None

        if fade_ms:
            # fade to underlying color
            color_of_key = self._get_color_and_fade(stack, 0)[0]

            self._remove_from_stack_by_key(key)

            start_time = self.machine.clock.get_time()
            self.stack.append(LightStackEntry(priority,
                                              key,
                                              start_time,
                                              color_of_key,
                                              start_time + fade_ms / 1000.0,
                                              None))
            self.delay.reset(ms=fade_ms, callback=partial(self._remove_fade_out, key=key),
                             name="remove_fade_{}".format(key))
            if len(self.stack) > 1:
                self.stack.sort(reverse=True)
        else:
            # no fade -> just remove color from stack
            self._remove_from_stack_by_key(key)

        if color_changes:
            self._schedule_update()

    def _remove_fade_out(self, key):
        """Remove a timed out fade out."""
        if not self.stack:
            return

        found = False
        color_change = True
        for _, entry in enumerate(self.stack):
            if entry.key == key and entry.dest_color is None:
                found = True
                break
            if entry.dest_color is not None:
                # found entry above the removed which is non-transparent
                color_change = False

        if found:
            if self._debug:
                self.debug_log("Removing fadeout for key '%s' from stack", key)
            self.stack = [x for x in self.stack if x.key != key or x.dest_color is not None]

        if found and color_change:
            self._schedule_update()

    def _remove_from_stack_by_key(self, key):
        """Remove a key from stack."""
        # tune the common case
        if not self.stack:
            return
        if self._debug:
            self.debug_log("Removing key '%s' from stack", key)
        if len(self.stack) == 1:
            if self.stack[0].key == key:
                self.stack = []
        else:
            self.stack = [x for x in self.stack if x.key != key]

    def _schedule_update(self):
        start_color, start_time, target_color, target_time = self._get_color_and_target_time(self.stack)

        # check if our fade target really changed
        if (start_color, start_time, target_color, target_time) == self._last_fade_target:
            # nope its the same -> nothing to do
            return

        if self._last_fade_target and target_color == self._last_fade_target[2] and \
                (self._last_fade_target[3] < 0 or self._last_fade_target[3] < self.machine.clock.get_time()):
            # last fade had the same target and finished already -> nothing to do
            return

        self._last_fade_target = (start_color, start_time, target_color, target_time)

        if start_color != target_color:
            start_color = self.color_correct(self.gamma_correct(start_color))
            target_color = self.color_correct(self.gamma_correct(target_color))
        else:
            start_color = self.color_correct(self.gamma_correct(start_color))
            target_color = start_color

        for color, drivers in self.hw_drivers.items():
            if color in ["red", "blue", "green"]:
                start_brightness = getattr(start_color, color) / 255.0
                target_brightness = getattr(target_color, color) / 255.0
            elif color == "white":
                start_brightness = min(start_color.red, start_color.green, start_color.blue) / 255.0
                target_brightness = min(target_color.red, target_color.green, target_color.blue) / 255.0
            else:
                raise ColorException("Invalid color {}".format(color))
            for driver in drivers:
                driver.set_fade(start_brightness, start_time, target_brightness, target_time)

        for platform in self.platforms:
            platform.light_sync()

    def clear_stack(self):
        """Remove all entries from the stack and resets this light to 'off'."""
        self.stack = []

        if self._debug:
            self.debug_log("Clearing Stack")

        self._schedule_update()

    def _get_priority_from_key(self, key):
        if not self.stack:
            return 0
        if self.stack[0].key == key:
            return self.stack[0].priority
        try:
            return [x for x in self.stack if x.key == key][0].priority
        except IndexError:
            return 0

    def gamma_correct(self, color):
        """Apply max brightness correction to color.

        Args:
        ----
            color: The RGBColor() instance you want to have gamma applied.

        Returns an updated RGBColor() instance with gamma corrected.
        """
        factor = self.machine.light_controller.brightness_factor
        if factor == 1.0:
            return color

        return RGBColor([int(x * factor) for x in color])

    def color_correct(self, color):
        """Apply the current color correction profile to the color passed.

        Args:
        ----
            color: The RGBColor() instance you want to get color corrected.

        Returns an updated RGBColor() instance with the current color
        correction profile applied.

        Note that if there is no current color correction profile applied, the
        returned color will be the same as the color that was passed.
        """
        if self._color_correction_profile is None:
            return color

        if self._debug:
            self.debug_log("Applying color correction: %s (applied "
                           "'%s' color correction profile)",
                           self._color_correction_profile.apply(color),
                           self._color_correction_profile.name)

        return self._color_correction_profile.apply(color)

    def _get_color_and_target_time(self, stack) -> Tuple[RGBColor, int, RGBColor, int]:
        try:
            color_settings = stack[0]
        except IndexError:
            # no stack
            return self._off_color, -1, self._off_color, -1

        dest_color = color_settings.dest_color
        dest_time = color_settings.dest_time

        # no fade
        if not dest_time:
            # if we are transparent just return the lower layer
            if dest_color is None:
                return self._get_color_and_target_time(stack[1:])
            return dest_color, -1, dest_color, -1

        # fade out
        if dest_color is None:
            _, _, lower_dest_color, lower_dest_time = self._get_color_and_target_time(stack[1:])
            start_time = color_settings.start_time
            if lower_dest_time < 0:
                # no fade going on below current layer
                dest_color = lower_dest_color
            elif start_time < lower_dest_time < dest_time:
                # fade below is shorter than fade out. removing the fade will trigger a new fade in this case
                ratio = (dest_time - lower_dest_time) / (dest_time - start_time)
                dest_color = RGBColor.blend(color_settings.start_color, dest_color, ratio)
                dest_time = lower_dest_time
            else:
                # upper fade is longer. use color target below. this might be slightly inaccurate
                dest_color = lower_dest_color

        # return destination color and time
        return color_settings.start_color, color_settings.start_time, dest_color, dest_time

    # pylint: disable-msg=too-many-return-statements
    def _get_color_and_fade(self, stack, max_fade_ms: int, *, current_time=None) -> Tuple[RGBColor, int, bool]:
        try:
            color_settings = stack[0]
        except IndexError:
            # no stack
            return self._off_color, -1, True

        dest_color = color_settings.dest_color

        # no fade
        if not color_settings.dest_time:
            # if we are transparent just return the lower layer
            if dest_color is None:
                return self._get_color_and_fade(stack[1:], max_fade_ms)
            return dest_color, -1, True

        if current_time is None:
            current_time = self.machine.clock.get_time()

        # fade is done
        if current_time >= color_settings.dest_time:
            # if we are transparent just return the lower layer
            if dest_color is None:
                return self._get_color_and_fade(stack[1:], max_fade_ms)
            return color_settings.dest_color, -1, True

        if dest_color is None:
            dest_color, lower_fade_ms, _ = self._get_color_and_fade(stack[1:], max_fade_ms)
            if lower_fade_ms > 0:
                max_fade_ms = lower_fade_ms

        target_time = current_time + (max_fade_ms / 1000.0)
        # check if fade will be done before max_fade_ms
        if target_time > color_settings.dest_time:
            return dest_color, int((color_settings.dest_time - current_time) * 1000), True

        # check if we are calculating before the start_time
        if target_time <= color_settings.start_time:
            return color_settings.start_color, max_fade_ms, False

        # figure out the ratio of how far along we are
        try:
            ratio = ((target_time - color_settings.start_time) /
                     (color_settings.dest_time - color_settings.start_time))
        except ZeroDivisionError:
            ratio = 1.0

        return RGBColor.blend(color_settings.start_color, dest_color, ratio), max_fade_ms, False

    def _get_brightness_and_fade(self, max_fade_ms: int, color: str, *, current_time=None) -> Tuple[float, int, bool]:
        uncorrected_color, fade_ms, done = self._get_color_and_fade(self.stack, max_fade_ms, current_time=current_time)
        corrected_color = self.gamma_correct(uncorrected_color)
        corrected_color = self.color_correct(corrected_color)

        if color in ["red", "blue", "green"]:
            brightness = getattr(corrected_color, color) / 255.0
        elif color == "white":
            brightness = min(corrected_color.red, corrected_color.green, corrected_color.blue) / 255.0
        else:
            raise ColorException("Invalid color {}".format(color))
        return brightness, fade_ms, done

    @property
    def _color(self):
        """Getter for color."""
        return self.get_color()

    def get_color_below(self, priority, key):
        """Return an RGBColor() instance of the 'color' setting of the highest color below a certain key.

        Similar to get_color.
        """
        if not self.stack:
            # no stack -> we are black
            return self._off_color

        if self.stack[0].key == key and self.stack[0].priority == priority:
            # fast path for resetting the top element
            return self._get_color_and_fade(self.stack, 0)[0]

        stack = []
        for i, entry in enumerate(self.stack):
            if entry.priority <= priority and entry.key <= key:
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
        return bool(self.stack and self.stack[0].dest_time > self.machine.clock.get_time())
