""" Contains the MatrixLight parent classes. """

from mpf.system.device import Device
from mpf.system.tasks import Task


class MatrixLight(Device):
    """ Represents a light connected to a traditional lamp matrix in a pinball
    machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.

    """

    config_section = 'matrix_lights'
    collection = 'lights'
    class_label = 'light'

    # todo need to get the handler stuff out of each of these I think and into
    # a parent class? Maybe this is a device thing?

    def __init__(self, machine, name, config, collection=None, validate=True):
        config['number_str'] = str(config['number']).upper()

        super().__init__(machine, name, config, collection,
                         platform_section='matrix_lights',
                         validate=validate)

        self.hw_driver, self.number = (
            self.platform.configure_matrixlight(self.config))

        self.registered_handlers = []

        self.state = {  # current state of this light
            'brightness': 0,
            'priority': 0,
            'destination_brightness': 0,
            'destination_time': 0.0,
            'start_brightness': 0,
            'start_time': 0.0
        }

        self.cache = {  # cached state of last manual command
            'brightness': 0,
            'priority': 0,
            'destination_brightness': 0,
            'destination_time': 0.0,
            'start_brightness': 0,
            'start_time': 0.0
        }

        self.fade_task = None
        self.fade_in_progress = False

        # set up the X, Y coordinates
        self.x = None
        self.y = None

        if 'x' in config:
            self.x = config['x']

        if 'y' in config:
            self.y = config['y']

    def on(self, brightness=255, fade_ms=0, priority=0, cache=True, force=False):
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
        """

        # First, if this incoming command is at a lower priority than what the
        # light is doing now, we don't proceed
        if priority < self.state['priority'] and not force:
            return

        # todo cache support
        # todo add brightness 0 as the same as on(0)
        if type(brightness) is list:
            brightness = brightness[0]

        if self.registered_handlers:
            for handler in self.registered_handlers:
                handler(light_name=self.name, brightness=brightness)

        current_time = self.machine.clock.get_time()

        # update our state
        self.state['priority'] = priority

        if fade_ms:
            self.state['fade_ms'] = fade_ms
            self.state['destination_brightness'] = brightness
            self.state['start_brightness'] = self.state['brightness']
            self.state['start_time'] = current_time
            self.state['destination_time'] = current_time + (fade_ms / 1000.0)
            self._setup_fade()

            if self.debug:
                print("we have a light fade to set up")

        else:
            self.state['brightness'] = brightness

            if self.debug:
                self.log.debug("Setting Brightness: %s", brightness)

            self.hw_driver.on(brightness)

        if cache:
            self.cache['brightness'] = brightness
            self.cache['start_brightness'] = self.state['brightness']
            self.cache['destination_brightness'] = self.state['destination_brightness']
            self.cache['start_time'] = current_time
            self.cache['destination_time'] = self.state['destination_time']
            self.cache['priority'] = priority
            self.cache['fade_ms'] = fade_ms

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

        if not self.fade_task:
            if self.debug:
                print("setting up fade task")
            self.fade_task = Task.create(self.machine, self._fade_task)
        elif self.debug:
                print("already have a fade task")

    def _fade_task(self):
        """
        Task that performs a fade from the current brightness to the target brightness
        over the specified fade time.
        Returns: None
        """
        if self.debug:
            print("fade_in_progress fade_task")
            print("state", self.state)

        state = self.state

        # figure out the ratio of how far along we are
        ratio = ((self.machine.clock.get_time() - state['start_time']) /
                 (state['destination_time'] - state['start_time']))

        if self.debug:
            print("ratio", ratio)

        if ratio >= 1.0:  # fade is done
            self.fade_in_progress = False
            set_cache = True
            new_brightness = state['destination_brightness']
            self.fade_task.stop()
            self.fade_task = None
        else:
            set_cache = False
            new_brightness = state['start_brightness'] + int((state['destination_brightness'] -
                                                              state['start_brightness']) * ratio)

        if self.debug:
            print("new brightness", new_brightness)

        self.on(brightness=new_brightness, fade_ms=0, priority=state['priority'], cache=set_cache)

        if self.debug:
            print("fade_in_progress just ended")
            print("killing fade task")

    def _kill_fade(self):
        self.fade_in_progress = False
        self.fade_task.stop()
        self.fade_task = None
        self.on(brightness=self.state['destination_brightness'],
                fade_ms=0, priority=self.state['priority'], cache=True)
