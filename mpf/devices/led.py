""" Contains the Led parent classes. """
from operator import itemgetter

from mpf.core.rgb_color import RGBColor
from mpf.core.rgb_color import RGBColorCorrectionProfile
from mpf.core.system_wide_device import SystemWideDevice


class Led(SystemWideDevice):
    """An RGB LED in a pinball machine."""

    config_section = 'leds'
    collection = 'leds'
    class_label = 'led'

    leds_to_update = set()

    @classmethod
    def device_class_init(cls, machine):
        machine.validate_machine_config_section('led_settings')
        if machine.config['led_settings']['color_correction_profiles'] is None:
            machine.config['led_settings']['color_correction_profiles'] = (
                dict())

        # Generate and add color correction profiles to the machine
        machine.led_color_correction_profiles = dict()
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

        # todo make time configurable
        machine.clock.schedule_interval(cls.update_leds, 0, -100)

    @classmethod
    def update_leds(cls, dt):
        """Called periodically (default at the end of every frame) to write the
        new led colors to the hardware for the LEDs that changed during that
        frame.

        """
        del dt

        # todo we could make a change here (or an option) so that it writes
        # every led, every frame. That way they'd fix themselves if something
        # got weird due to interference? Or is that a platform thing?

        if Led.leds_to_update:
            for led in Led.leds_to_update:
                led.write_color_to_hw_driver()

            Led.leds_to_update = set()

    def __init__(self, machine, name):
        super().__init__(machine, name)

        self.fade_in_progress = False
        self.fade_destination_color = RGBColor()
        self.fade_end_time = None
        self.default_fade_ms = None

        self.registered_handlers = list()
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

        """

    def prepare_config(self, config, is_mode_config):
        del is_mode_config
        config['number_str'] = str(config['number']).upper()
        return config

    def _initialize(self):
        self.load_platform_section('leds')

        self.config['default_color'] = RGBColor(
            RGBColor.string_to_rgb(self.config['default_color'],
                                   (255, 255, 255)))

        self.hw_driver = self.platform.configure_led(self.config)

        if self.config['color_correction_profile'] is not None:
            if self.config['color_correction_profile'] in (
                    self.machine.led_color_correction_profiles):
                profile = self.machine.led_color_correction_profiles[
                    self.config['color_correction_profile']]

                if profile is not None:
                    self.set_color_correction_profile(profile)
            else:
                self.log.warning(
                    "Color correction profile '%s' was specified for the LED"
                    " but the color correction profile does not exist."
                    " Color correction will not be applied to this LED.",
                    self.config['color_correction_profile'])

        if self.config['fade_ms'] is not None:
            self.default_fade_ms = self.config['fade_ms']
        elif self.machine.config['led_settings']:
            self.default_fade_ms = (self.machine.config['led_settings']
                                    ['default_led_fade_ms'])

        if self.debug:
            self.log.debug("Initializing LED. Platform: %s, CC Profile: %s, "
                           "Default fade: %sms", self.platform,
                           self._color_correction_profile,
                           self.default_fade_ms)

    def set_color_correction_profile(self, profile):
        """Applies a color correction profile to this LED.

        Args:
            profile: An RGBColorCorrectionProfile() instance

        """
        self._color_correction_profile = profile

    def color(self, color, fade_ms=None, priority=0, key=None):
        """Adds or updates a color entry in this LED's stack, which is how you
        tell this LED what color you want it to be.

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
            key: An arbitrary identifier (can be any unmutable object) that's
                used to identify these settings for later removal. If any
                settings in the stack already have this key, those settings
                will be replaced with these new settings.

        """
        if self.debug:
            self.log.debug("Received color() command. color: %s, fade_ms: %s"
                           "priority: %s, key: %s", color, fade_ms, priority,
                           key)

        if not isinstance(color, RGBColor):
            color = RGBColor(color)

        if fade_ms is None:
            if self.default_fade_ms is not None:
                fade_ms = self.default_fade_ms
            else:
                fade_ms = 0

        if priority < self._get_priority_from_key(key):
            if self.debug:
                self.log.debug("Incoming priority is lower than an existing "
                               "stack item with the same key. Not adding to "
                               "stack.")

            return

        self._add_to_stack(color, fade_ms, priority, key)

    def _add_to_stack(self, color, fade_ms, priority, key):
        curr_color = self.get_color()

        self.remove_from_stack(key)

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
                               key=key))

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
        """Removes all entries from the stack and resets this LED to 'off'."""
        self.stack[:] = []

        if self.debug:
            self.log.debug("Clearing Stack")

        Led.leds_to_update.add(self)

    def remove_from_stack(self, key):
        """Removes a group of color settings from the stack.

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

    def get_color(self):
        """Returns an RGBColor() instance of the 'color' setting of the highest
        color setting in the stack. This is usually the same color as the
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

    def write_color_to_hw_driver(self):
        """Physically updates the LED hardware object based on the 'color'
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
            if self.debug:
                self.log.debug("Writing color to hw driver: %s",
                               self.color_correct(self.stack[0]['color']))

            self.hw_driver.color(self.color_correct(self.stack[0]['color']))

            if self.registered_handlers:
                # Handlers are not sent color corrected colors
                # todo make this a config option?
                for handler in self.registered_handlers:
                    handler(led_name=self.name,
                            color=self.stack[0]['color'])

    def color_correct(self, color):
        """Applies the current color correction profile to the color passed.

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
        del kwargs
        self.color(color=self.config['default_color'], fade_ms=fade_ms,
                   priority=priority, key=key)

    def off(self, fade_ms=None, priority=0, key=None, **kwargs):
        del kwargs
        self.color(color=RGBColor(), fade_ms=fade_ms, priority=priority,
                   key=key)

    def add_handler(self, callback):
        """Registers a handler to be called when this light changes state."""
        self.registered_handlers.append(callback)

    def remove_handler(self, callback=None):
        """Removes a handler from the list of registered handlers."""
        if not callback:  # remove all
            self.registered_handlers = []
            return

        if callback in self.registered_handlers:
            self.registered_handlers.remove(callback)

    def _setup_fade(self):
        if self.fade_in_progress:
            return

        self.fade_in_progress = True

        if self.debug:
            self.log.debug("Setting up the fade task")

        self.machine.clock.schedule_interval(self._fade_task, 0)

    def _fade_task(self, dt):
        del dt

        # not sure why this is needed, but sometimes the fade task tries to
        # run even though self.fade_in_progress is False. Maybe
        # clock.unschedule doesn't happen right away?
        if not self.fade_in_progress:
            return

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
        self.machine.clock.unschedule(self._fade_task)

        if self.debug:
            self.log.debug("Stopping fade task")
