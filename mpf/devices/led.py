""" Contains the LED parent classes. """

from mpf.core.device import Device
from mpf.core.rgb_color import RGBColor
from mpf.core.rgb_color import RGBColorCorrectionProfile


class Led(Device):
    """ Represents an light connected to an new-style interface board.
    Typically this is an LED.

    DirectLEDs can have any number of elements. Typically they're either
    single element (single color), or three element (RGB), though dual element
    (red/green) and quad-element (RGB + UV) also exist and can be used.

    """

    config_section = 'leds'
    collection = 'leds'
    class_label = 'led'

    leds_to_update = set()

    @classmethod
    def device_class_init(cls, machine):
        machine.validate_machine_config_section('led_settings')
        if machine.config['led_settings']['color_correction_profiles'] is None:
            machine.config['led_settings']['color_correction_profiles'] = dict()

        # Generate and add color correction profiles to the machine
        machine.led_color_correction_profiles = dict()
        for profile_name, profile_parameters in machine.config['led_settings']['color_correction_profiles'].items():

            machine.config_validator.validate_config('color_correction_profile',
                                                     machine.config['led_settings']
                                                     ['color_correction_profiles'][profile_name],
                                                     profile_parameters)

            profile = RGBColorCorrectionProfile(profile_name)
            profile.generate_from_parameters(gamma=profile_parameters['gamma'],
                                             whitepoint=profile_parameters['whitepoint'],
                                             linear_slope=profile_parameters['linear_slope'],
                                             linear_cutoff=profile_parameters['linear_cutoff'])
            machine.led_color_correction_profiles[profile_name] = profile

        # todo make time configurable
        machine.clock.schedule_interval(cls.update_leds, 0, -100)

    @classmethod
    def update_leds(cls, dt):
        # called periodically (default at the end of every frame) to actually
        # write the new light states to the hardware
        del dt
        if Led.leds_to_update:
            for light in Led.leds_to_update:
                light.do_color()

            Led.leds_to_update = set()

    def __init__(self, machine, name, config=None, validate=True):
        config['number_str'] = str(config['number']).upper()
        super().__init__(machine, name, config, platform_section='leds', validate=validate)

        self.config['default_color'] = RGBColor(
            RGBColor.string_to_rgb(self.config['default_color'], (255, 255, 255)))

        self.hw_driver = self.platform.configure_led(self.config)

        self.fade_in_progress = False
        self.fade_destination_color = RGBColor()
        self.fade_end_time = None

        self.registered_handlers = list()

        self.state = dict(color=RGBColor(),
                          priority=0,
                          destination_color=RGBColor(),
                          destination_time=0.0,
                          start_color=RGBColor(),
                          start_time=0.0,
                          fade_ms=0)
        """Current state of this LED."""

        self.cache = dict(color=RGBColor(),
                          priority=0,
                          destination_color=RGBColor(),
                          destination_time=0.0,
                          start_color=RGBColor(),
                          start_time=0.0,
                          fade_ms=0)
        """Cached state of the last manual command."""

        # Set color correction profile (if applicable)
        self._color_correction_profile = None
        if self.config['color_correction_profile'] is not None:
            if self.config['color_correction_profile'] in self.machine.led_color_correction_profiles:
                profile = self.machine.led_color_correction_profiles[self.config['color_correction_profile']]
                if profile is not None:
                    self.set_color_correction_profile(profile)
            else:
                self.log.warning("Color correction profile '%s' was specified for the LED"
                                 " but the color correction profile does not exist."
                                 " Color correction will not be applied to this LED.",
                                 self.config['color_correction_profile'])

    def set_color_correction_profile(self, profile):
        self._color_correction_profile = profile

    def color(self, color, fade_ms=None, priority=0, cache=True, force=False,  blend=False):
        """Sets this LED to the color passed.

        Args:
            color: An RGBColor object containing the desired color.
            fade_ms: Integer value of how long the LED should fade from its
                current color to the color you're passing it here.
            priority: Arbitrary integer value of the priority of this request.
                If the incoming priority is lower than the current priority,
                this incoming color request will have no effect. Default is 0.
            cache: Boolean which controls whether this new color command will
                update the LED's cache. Default is True.
            force: Boolean which will force this new color command to be applied
                to the LED, regardless of the incoming or current priority.
                Default is True.
            blend: Not yet implemented.
        """
        del blend
        # If the incoming priority is lower that what this LED is at currently
        # ignore this request.
        if priority < self.state['priority'] and not force:
            return

        if fade_ms is None:
            if self.config['fade_ms'] is not None:
                fade_ms = self.config['fade_ms']
                if self.debug:
                    self.log.debug("Incoming fade_ms is none. Setting to %sms "
                                   "based on this LED's default fade config",
                                   fade_ms)
            elif self.machine.config['led_settings']:
                fade_ms = (self.machine.config['led_settings']
                           ['default_led_fade_ms'])
                if self.debug:
                    self.log.debug("Incoming fade_ms is none. Setting to %sms "
                                   "based on this global default fade", fade_ms)
            # potential optimization make this not conditional

        current_time = self.machine.clock.get_time()

        # update our state
        self.state['priority'] = priority
        self.state['fade_ms'] = fade_ms

        if not self.fade_in_progress:
            if fade_ms:

                self.state['destination_color'] = color
                self.state['start_color'] = self.state['color']
                self.state['start_time'] = current_time
                self.state['destination_time'] = current_time + (fade_ms / 1000.0)
                self._setup_fade()

                if self.debug:
                    print("we have a fade to set up")

            else:
                self.state['color'] = color
                self.state['destination_color'] = color
                self.state['destination_time'] = 0.0
                self.state['start_color'] = RGBColor()
                self.state['start_time'] = current_time

                if self.debug:
                    self.log.debug("Setting Color: %s", color)

                # Apply color correction profile (if one is set)
                if self._color_correction_profile is None:
                    self.hw_driver.color(color)
                    if self.debug:
                        self.log.debug("Output Color to Hardware: %s", color)
                else:
                    self.hw_driver.color(self._color_correction_profile.apply(color))
                    if self.debug:
                        self.log.debug("Output Color to Hardware: %s (applied '%s' color correction profile)",
                                       self._color_correction_profile.apply(color),
                                       self._color_correction_profile.name)
        else:
            self.state['color'] = color

        if cache:
            self.cache['color'] = color  # new color
            self.cache['start_color'] = self.state['color']
            self.cache['destination_color'] = self.state['destination_color']
            self.cache['start_time'] = current_time
            self.cache['destination_time'] = self.state['destination_time']
            self.cache['fade_ms'] = fade_ms
            self.cache['priority'] = priority

        Led.leds_to_update.add(self)

    def do_color(self):

        if self.state['fade_ms'] and not self.fade_in_progress:
            self._setup_fade()

        else:

            if self.debug:
                print(self.state['color'], self.machine.clock.get_time())

            self.hw_driver.color(self.state['color'])

            if self.registered_handlers:
                for handler in self.registered_handlers:
                    handler(led_name=self.name,
                            color=self.state['color'])

    def disable(self, fade_ms=0, priority=0, cache=True, force=False):
        """ Disables an LED, including all elements of a multi-color LED.
        """
        self.color(color=RGBColor(), fade_ms=fade_ms, priority=priority,
                   cache=cache, force=force)

    def on(self, brightness=255, fade_ms=0,
           priority=0, cache=True, force=False):
        """
        Turn on the LED (uses the default color).
        Args:
            brightness:
            fade_ms:
            priority:
            cache:
            force:

        Returns:

        """
        self.color(color=[self.config['default_color'][0] * brightness / 255.0,
                          self.config['default_color'][1] * brightness / 255.0,
                          self.config['default_color'][2] * brightness / 255.0],
                   fade_ms=fade_ms,
                   priority=priority,
                   cache=cache,
                   force=force)

    def off(self, fade_ms=0, priority=0, cache=True, force=False):
        """
        Turn off the LED (set all channels to 0).
        Args:
            fade_ms:
            priority:
            cache:
            force:

        Returns: None
        """
        self.color(color=RGBColor(), fade_ms=fade_ms, priority=priority,
                   cache=cache, force=force)
        # todo send args to disable()

    def get_state(self):
        """Returns the current state of this LED"""
        return self.state

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

    def restore(self):
        """Sets this LED to the cached state."""

        if self.debug:
            self.log.debug("Received a restore command.")
            self.log.debug("Cached color: %s, Cached priority: %s", self.cache['color'], self.cache['priority'])

        self.color(color=self.cache['color'],
                   fade_ms=0,
                   priority=self.cache['priority'],
                   force=True,
                   cache=True)

    def _setup_fade(self):
        """
        Sets up the fade task for this LED.
        Returns: None
        """
        self.fade_in_progress = True
        self.machine.clock.unschedule(self._fade_task)

        if self.debug:
            print("setting up fade task")

        self.machine.clock.schedule_interval(self._fade_task, 0)

    def _fade_task(self, dt):
        """
        Task that performs a fade from the current LED color to the target LED color
        over the specified fade time.
        Returns: None
        """
        del dt

        # not sure why this is needed, but sometimes the fade task tries to
        # run even though self.fade_in_progress is False. Maybe
        # clock.unschedule doesn't happen right away?
        if not self.fade_in_progress:
            return

        if self.debug:
            print("fade_in_progress fade_task")
            print("state", self.state)

        state = self.state

        # figure out the ratio of how far along we are
        try:
            ratio = ((self.machine.clock.get_time() - state['start_time']) /
                     (state['destination_time'] - state['start_time']))
        except ZeroDivisionError:
            ratio = 1.0

        if self.debug:
            print("ratio", ratio)

        if ratio >= 1.0:  # fade is done
            self._stop_fade_task()
            set_cache = True
            new_color = state['destination_color']
        else:
            set_cache = False
            new_color = RGBColor.blend(state['start_color'], state['destination_color'], ratio)

        if self.debug:
            print("new color", new_color)

        self.color(color=new_color, fade_ms=0, priority=state['priority'],
                   cache=set_cache)

        if self.debug:
            print("fade_in_progress just ended")
            print("killing fade task")

    def _end_fade(self):
        # stops the fade and instantly sets the light to its destination color
        self._stop_fade_task()
        self.color(color=self.state['destination_color'], fade_ms=0,
                   priority=self.state['priority'], cache=True)

    def _stop_fade_task(self):
        # stops the fade task. Light is left in whatever state it was in
        self.fade_in_progress = False
        self.machine.clock.unschedule(self._fade_task)
