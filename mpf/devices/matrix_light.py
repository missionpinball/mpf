""" Contains the MatrixLight parent classes. """

from mpf.core.system_wide_device import SystemWideDevice


class MatrixLight(SystemWideDevice):
    """ Represents a light connected to a traditional lamp matrix in a pinball
    machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.

    """

    config_section = 'matrix_lights'
    collection = 'lights'
    class_label = 'light'

    lights_to_update = set()

    # todo need to get the handler stuff out of each of these I think and into
    # a parent class? Maybe this is a device thing?

    @classmethod
    def device_class_init(cls, machine):
        # todo make time configurable
        machine.clock.schedule_interval(cls.update_matrix_lights, 0, -100)

    @classmethod
    def update_matrix_lights(cls, dt):
        del dt
        # called periodically (default at the end of every frame) to actually
        # write the new light states to the hardware
        if MatrixLight.lights_to_update:
            for light in MatrixLight.lights_to_update:
                light.do_on()

            MatrixLight.lights_to_update = set()

    def __init__(self, machine, name):
        super().__init__(machine, name)

        self.registered_handlers = list()

        self.state = dict(brightness=0,
                          priority=0,
                          destination_brightness=0,
                          destination_time=0.0,
                          start_brightness=0,
                          start_time=0.0,
                          fade_ms=0)
        """Current state of this light."""

        self.cache = dict(brightness=0,
                          priority=0,
                          destination_brightness=0,
                          destination_time=0.0,
                          start_brightness=0,
                          start_time=0.0,
                          fade_ms=0)
        """Cached state of the last manual command."""

        self.fade_in_progress = False

        # set up the X, Y coordinates
        self.x = None
        self.y = None

    def prepare_config(self, config, is_mode_config):
        del is_mode_config
        config['number_str'] = str(config['number']).upper()
        return config

    def _initialize(self):
        self.load_platform_section('matrix_lights')

        self.hw_driver, self.number = (
            self.platform.configure_matrixlight(self.config))

        if 'x' in self.config:
            self.x = self.config['x']

        if 'y' in self.config:
            self.y = self.config['y']

    def on(self, brightness=255, fade_ms=0, priority=0, cache=True,
           force=False):
        """Turns on this matrix light.

        Args:
            brightness: How bright this light should be, as an int between 0
                and 255. 0 is off. 255 is full on. Note that intermediary
                values are not yet implemented, so 0 is off, anything from
                1-255 is full on.
            fade_ms: The number of milliseconds to fade from the current
                brightness level to the desired brightness level.
            priority: The priority of the incoming request. If this priority is
                lower than the current cached priority, this on command will
                have no effect. (Unless force=True)
            cache: Boolean as to whether this light should cache these new
                settings. This cache can be used for the light to "go back" to
                it's previous state. Default is True.
            force: Whether the light should be forced to go to the new state,
                regardless of the incoming and current priority. Default is
                False.

        Note: This method immediately updates the internal state of the matrix
        light, but it doesn't actually send the command to set or change the
        light to the hardware platform interface until the end of the
        current frame. This is done so that multiple things changing the same
        light in the same frame actually only send a single command to the
        light instead of sending a stream of conflicting  values.

        """
        # First, if this incoming command is at a lower priority than what the
        # light is doing now, we don't proceed (unless force is True).

        if priority < self.state['priority'] and not force:
            return

        # todo add brightness 0 as the same as on(0)
        if isinstance(brightness, list):
            brightness = brightness[0]

        current_time = self.machine.clock.get_time()

        # update state
        self.state['priority'] = priority
        self.state['fade_ms'] = fade_ms

        if not self.fade_in_progress:
            if fade_ms:
                self.state['destination_brightness'] = brightness
                self.state['start_brightness'] = self.state['brightness']
                self.state['destination_time'] = current_time + (fade_ms / 1000.0)
                self.state['start_time'] = current_time
                if self.debug:
                    print("setting fade", self.state)

            else:
                self.state['brightness'] = brightness
                self.state['destination_brightness'] = brightness
                self.state['destination_time'] = 0.0
                self.state['start_brightness'] = 0
                self.state['start_time'] = current_time
                if self.debug:
                    print("setting brightness", self.state)

        else:
            self.state['brightness'] = brightness

        if cache:
            self.cache['brightness'] = brightness
            self.cache['start_brightness'] = self.state['brightness']
            self.cache['destination_brightness'] = self.state['destination_brightness']
            self.cache['start_time'] = current_time
            self.cache['destination_time'] = self.state['destination_time']
            self.cache['priority'] = priority
            self.cache['fade_ms'] = fade_ms

        MatrixLight.lights_to_update.add(self)

    def do_on(self):
        if self.state['fade_ms'] and not self.fade_in_progress:
            self._setup_fade()

        else:

            if self.debug:
                print(self.state['brightness'], self.machine.clock.get_time())

            self.hw_driver.on(self.state['brightness'])

            if self.registered_handlers:
                for handler in self.registered_handlers:
                    handler(light_name=self.name,
                            brightness=self.state['brightness'])

    def off(self, fade_ms=0, priority=0, cache=True, force=False):
        """Turns this light off.

        Args:
            fade_ms: The number of milliseconds to fade from the current
                brightness level to a brightness level of 0 (off).
            priority: The priority of the incoming request. If this priority is
                lower than the current cached priority, this on command will
                have no effect. (Unless force=True)
            cache: Boolean as to whether this light should cache these new
                settings. This cache can be used for the light to "go back" to
                it's previous state. Default is True.
            force: Whether the light should be forced to go to the new state,
                regardless of the incoming and current priority. Default is
                False.
        """
        self.on(brightness=0, fade_ms=fade_ms, priority=priority, cache=cache,
                force=force)

    def get_state(self):
        """Returns the current state of this light"""
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
        """Restores the light state from cache."""

        if self.debug:
            self.log.debug("Received a restore command.")
            self.log.debug("Cached brightness: %s, Cached priority: %s",
                           self.cache['brightness'], self.cache['priority'])

        self.on(brightness=self.cache['brightness'],
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
        Task that performs a fade from the current brightness to the target brightness
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
            print("fade_in_progress fade_task", self.machine.clock.get_time())
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
            new_brightness = state['destination_brightness']
        else:
            set_cache = False
            new_brightness = state['start_brightness'] + int((state['destination_brightness'] -
                                                              state['start_brightness']) * ratio)

        if self.debug:
            print("new brightness", new_brightness)

        self.on(brightness=new_brightness, priority=state['priority'], cache=set_cache)

        if self.debug:
            print("fade_in_progress just ended")
            print("killing fade task")

    def _end_fade(self):
        # stops the fade and instantly sets the light to its destination color
        self._stop_fade_task()
        self.on(brightness=self.state['destination_brightness'], priority=self.state['priority'], cache=True)

    def _stop_fade_task(self):
        # stops the fade task. Light is left in whatever state it was in
        self.fade_in_progress = False
        self.machine.clock.unschedule(self._fade_task)
