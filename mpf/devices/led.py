"""Contains the Led class."""
from operator import itemgetter

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.rgb_color import RGBColor
from mpf.core.rgb_color import RGBColorCorrectionProfile
from mpf.core.settings_controller import SettingEntry
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("_color", "_corrected_color")
class Led(SystemWideDevice):

    """An RGB LED in a pinball machine."""

    config_section = 'leds'
    collection = 'leds'
    class_label = 'led'
    machine = None

    leds_to_update = set()
    leds_to_fade = set()
    _updater_task = None

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Initialise all LEDs.

        Args:
            machine: MachineController which is used
        """
        cls.machine = machine
        cls.leds_to_fade = set()
        cls.leds_to_update = set()

        machine.validate_machine_config_section('led_settings')

        if machine.config['led_settings']['color_correction_profiles'] is None:
            machine.config['led_settings']['color_correction_profiles'] = (
                dict())

        # Generate and add color correction profiles to the machine
        machine.led_color_correction_profiles = dict()

        # Create the default color correction profile and add it to the machine
        default_profile = RGBColorCorrectionProfile.default()
        machine.led_color_correction_profiles['default'] = default_profile

        # Add any user-defined profiles specified in the machine config file
        for profile_name, profile_parameters in (
                machine.config['led_settings']
                ['color_correction_profiles'].items()):

            machine.config_validator.validate_config(
                'color_correction_profile',
                machine.config['led_settings']['color_correction_profiles']
                [profile_name], profile_parameters)

            profile = RGBColorCorrectionProfile(profile_name)
            profile.generate_from_parameters(
                gamma=profile_parameters['gamma'],
                whitepoint=profile_parameters['whitepoint'],
                linear_slope=profile_parameters['linear_slope'],
                linear_cutoff=profile_parameters['linear_cutoff'])
            machine.led_color_correction_profiles[profile_name] = profile

        # schedule the single machine-wide update to write the current led of
        # each LED to the hardware
        cls._updater_task = machine.clock.schedule_interval(
            cls.update_leds, 1 / machine.config['mpf']['default_led_hw_update_hz'])

        machine.mode_controller.register_stop_method(cls.mode_stop)

        machine.settings.add_setting(SettingEntry("brightness", "Brightness", 100, "brightness", 1.0,
                                                  {0.25: "25%", 0.5: "50%", 0.75: "75%", 1.0: "100% (default)"}))

    @classmethod
    def update_leds(cls, dt):
        """Write leds to hardware platform.

        Called periodically (default at the end of every frame) to write the
        new led colors to the hardware for the LEDs that changed during that
        frame.

        Args:
            dt: time since last call
        """
        for led in list(Led.leds_to_fade):
            if led.fade_in_progress:
                led.fade_task(dt)

        # todo we could make a change here (or an option) so that it writes
        # every led, every frame. That way they'd fix themselves if something
        # got weird due to interference? Or is that a platform thing?

        if Led.leds_to_update:
            for led in Led.leds_to_update:
                led.write_color_to_hw_driver()

            Led.leds_to_update = set()

    @classmethod
    def mode_stop(cls, mode: Mode):
        """Remove all entries from mode.

        Args:
            mode: Mode which was removed
        """
        for led in cls.machine.leds:
            led.remove_from_stack_by_mode(mode)

    def __init__(self, machine, name):
        """Initialise LED."""
        self.hw_driver = None
        self._color = [0, 0, 0]
        self._corrected_color = [0, 0, 0]
        super().__init__(machine, name)

        self.fade_in_progress = False
        self.default_fade_ms = None

        self._color_correction_profile = None

        self.stack = list()
        """A list of dicts which represents different commands that have come
        in to set this LED to a certain color (and/or fade). Each entry in the
        list contains the following key/value pairs:

        priority: The relative priority of this color command. Higher numbers
            take precedent, and the highest priority entry will be the command
            that's currently active. In the event of a tie, whichever entry was
            added last wins (based on 'start_time' below).
        start_time: The clock time when this command was added. Primarily used
            to calculate fades, but also used as a tie-breaker for multiple
            entries with the same priority.
        start_color: RGBColor() of the color of this LED when this command came
            in.
        dest_time: Clock time that represents when a fade (from start_color to
            dest_color) will be done. If this is 0, that means there is no
            fade. When a fade is complete, this value is reset to 0.
        dest_color: RGBColor() of the destination this LED is fading to. If
            a command comes in with no fade, then this will be the same as the
            'color' below.
        color: The current color of the LED based on this command. This value
            is updated automatically as fades progress, and it's the value
            that's actually written to the hardware (prior to color
            correction).
        key: An arbitrary unique identifier to keep multiple entries in the
            stack separate. If a new color command comes in with a key that
            already exists for an entry in the stack, that entry will be
            replaced by the new entry. The key is also used to remove entries
            from the stack (e.g. when shows or modes end and they want to
            remove their commands from the LED).
        mode: Optional mode where the brightness was set. Used to remove
            entries when a mode ends.
        """

    def _load_hw_driver(self):
        if self.config["platform"] == "lights":
            self.platform = None
            self.hw_driver = []
            lights_names = self.config['number'].split(",")
            for light_name in lights_names:
                self.hw_driver.append(self.machine.lights[light_name])
        else:
            self.load_platform_section('leds')
            self.hw_driver = self.platform.configure_led(self.config, len(self.config['type']))

    def _initialize(self):
        self._load_hw_driver()

        self.config['default_color'] = RGBColor(self.config['default_color'])

        if self.config['color_correction_profile'] is not None:
            if self.config['color_correction_profile'] in (
                    self.machine.led_color_correction_profiles):
                profile = self.machine.led_color_correction_profiles[
                    self.config['color_correction_profile']]

                if profile is not None:
                    self.set_color_correction_profile(profile)
            else:   # pragma: no cover
                error = "Color correction profile '{}' was specified for LED '{}'"\
                        " but the color correction profile does not exist."\
                    .format(self.config['color_correction_profile'], self.name)
                self.log.error(error)
                raise ValueError(error)

        if self.config['fade_ms'] is not None:
            self.default_fade_ms = self.config['fade_ms']
        else:
            self.default_fade_ms = (self.machine.config['led_settings']
                                    ['default_led_fade_ms'])

        if self.debug:
            self.log.debug("Initializing LED. Platform: %s, CC Profile: %s, "
                           "Default fade: %sms", self.platform,
                           self._color_correction_profile,
                           self.default_fade_ms)

    def set_color_correction_profile(self, profile):
        """Apply a color correction profile to this LED.

        Args:
            profile: An RGBColorCorrectionProfile() instance

        """
        self._color_correction_profile = profile

    # pylint: disable-msg=too-many-arguments
    def color(self, color, fade_ms=None, priority=0, key=None, mode=None):
        """Add or update a color entry in this LED's stack, which is how you tell this LED what color you want it to be.

        Args:
            color: RGBColor() instance, or a string color name, hex value, or
                3-integer list/tuple of colors.
            fade_ms: Int of the number of ms you want this LED to fade to the
                color in. A value of 0 means it's instant. A value of None (the
                default) means that it will use this LED's and/or the machine's
                default fade_ms setting.
            priority: Int value of the priority of these incoming settings. If
                this LED has current settings in the stack at a higher
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
        if self.debug:
            self.log.debug("Received color() command. color: %s, fade_ms: %s"
                           "priority: %s, key: %s", color, fade_ms, priority,
                           key)

        if not isinstance(color, RGBColor):
            color = RGBColor(color)

        if fade_ms is None:
            fade_ms = self.default_fade_ms

        if priority < self._get_priority_from_key(key):
            if self.debug:
                self.log.debug("Incoming priority is lower than an existing "
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

        if self.debug:
            self.log.debug("+-------------- Adding to stack ----------------+")
            self.log.debug("priority: %s", priority)
            self.log.debug("start_time: %s", self.machine.clock.get_time())
            self.log.debug("start_color: %s", curr_color)
            self.log.debug("dest_time: %s", dest_time)
            self.log.debug("dest_color: %s", color)
            self.log.debug("color: %s", new_color)
            self.log.debug("key: %s", key)

        Led.leds_to_update.add(self)

    def clear_stack(self):
        """Remove all entries from the stack and resets this LED to 'off'."""
        self.stack[:] = []

        if self.debug:
            self.log.debug("Clearing Stack")

        Led.leds_to_update.add(self)

    def remove_from_stack_by_key(self, key):
        """Remove a group of color settings from the stack.

        Args:
            key: The key of the settings to remove (based on the 'key'
                parameter that was originally passed to the color() method.)

        This method triggers a LED update, so if the highest priority settings
        were removed, the LED will be updated with whatever's below it. If no
        settings remain after these are removed, the LED will turn off.
        """
        if self.debug:
            self.log.debug("Removing key '%s' from stack", key)

        self.stack[:] = [x for x in self.stack if x['key'] != key]
        Led.leds_to_update.add(self)

    def remove_from_stack_by_mode(self, mode: Mode):
        """Remove a group of color settings from the stack.

        Args:
            mode: Mode which was removed

        This method triggers a LED update, so if the highest priority settings
        were removed, the LED will be updated with whatever's below it. If no
        settings remain after these are removed, the LED will turn off.
        """
        if self.debug:
            self.log.debug("Removing mode '%s' from stack", mode)

        self.stack[:] = [x for x in self.stack if x['mode'] != mode]
        Led.leds_to_update.add(self)

    def get_color(self):
        """Return an RGBColor() instance of the 'color' setting of the highest color setting in the stack.

        This is usually the same color as the
        physical LED, but not always (since physical LEDs are updated once per
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

    def _write_color_to_hw_driver(self, reordered_color):
        if self.platform:
            self.hw_driver.color(reordered_color)
        else:
            for i in range(len(self.hw_driver)):
                self.hw_driver[i].on(reordered_color[i])

    def write_color_to_hw_driver(self):
        """Set color to hardware platform.

        Physically update the LED hardware object based on the 'color'
        setting of the highest priority setting from the stack.

        This method is automatically called whenever a color change has been
        made (including when fades are active).
        """
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
            if self.debug:
                self.log.debug("Writing color to hw driver: %s", corrected_color)

            reordered_color = self._get_color_channels_for_hw(corrected_color)

            self._write_color_to_hw_driver(reordered_color)

    def _get_color_channels_for_hw(self, color):
        color_channels = []
        for color_name in self.config['type']:
            # red channel
            if color_name == 'r':
                color_channels.append(color.red)
            # green channel
            elif color_name == 'g':
                color_channels.append(color.green)
            # blue channel
            elif color_name == 'b':
                color_channels.append(color.blue)
            # simple white channel
            elif color_name == 'w':
                color_channels.append(min(color.red, color.green, color.blue))
            # always off
            elif color_name == '-':
                color_channels.append(0)
            # always on
            elif color_name == '+':
                color_channels.append(255)
            else:
                raise AssertionError("Invalid element {} in type {} of led {}".format(
                    color_name, self.config['type'], self.name))

        return color_channels

    def gamma_correct(self, color):
        """Apply max brightness correction to color.

        Args:
            color: The RGBColor() instance you want to have gamma applied.

        Returns:
            An updated RGBColor() instance with gamma corrected.
        """
        factor = self.machine.get_machine_var("brightness")
        # do not correct when there is no config or when using lights as channels (they are corrected on their own)
        if factor is None or not self.platform:
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

            if self.debug:
                self.log.debug("Applying color correction: %s (applied "
                               "'%s' color correction profile)",
                               self._color_correction_profile.apply(color),
                               self._color_correction_profile.name)

            return self._color_correction_profile.apply(color)

    def on(self, fade_ms=None, priority=0, key=None, **kwargs):
        """Turn LED on.

        Args:
            key: key for removal later on
            priority: priority on stack
            fade_ms: duration of fade
        """
        del kwargs
        self.color(color=self.config['default_color'], fade_ms=fade_ms,
                   priority=priority, key=key)

    def off(self, fade_ms=None, priority=0, key=None, **kwargs):
        """Turn LED off.

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

        if self.debug:
            self.log.debug("Setting up the fade task")

        Led.leds_to_fade.add(self)

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

        if self.debug:
            self.log.debug("Fade task, ratio: %s", ratio)

        if ratio >= 1.0:  # fade is done
            self._end_fade()
            color_settings['color'] = color_settings['dest_color']
        else:
            color_settings['color'] = (
                RGBColor.blend(color_settings['start_color'],
                               color_settings['dest_color'],
                               ratio))

        Led.leds_to_update.add(self)

    def _end_fade(self):
        # stops the fade and instantly sets the light to its destination color
        self._stop_fade_task()
        self.stack[0]['dest_time'] = 0

    def _stop_fade_task(self):
        # stops the fade task. Light is left in whatever state it was in
        self.fade_in_progress = False
        Led.leds_to_fade.remove(self)

        if self.debug:
            self.log.debug("Stopping fade task")
