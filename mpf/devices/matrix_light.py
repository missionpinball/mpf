""" Contains the MatrixLight parent classes. """

from mpf.system.device import Device


class MatrixLight(Device):
    """ Represents a light connected to a traditional lamp matrix in a pinball
    machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.

    """

    config_section = 'matrix_lights'
    collection = 'lights'
    class_label = 'light'

    #todo need to get the handler stuff out of each of these I think and into
    # a parent class? Maybe this is a device thing?

    def __init__(self, machine, name, config, collection=None, validate=True):
        config['number_str'] = str(config['number']).upper()

        super(MatrixLight, self).__init__(machine, name, config, collection,
                                          platform_section='matrix_lights',
                                          validate=validate)

        self.hw_driver, self.number = (
            self.platform.configure_matrixlight(self.config))

        self.registered_handlers = []

        self.state = {  # current state of this light
                        'brightness': 0,
                        'priority': 0}

        self.cache = {  # cached state of last manual command
                        'brightness': 0,
                        'priority': 0}

        # set up the X, Y coordinates
        self.x = None
        self.y = None

        if 'x' in config:
            self.x = config['x']

        if 'y' in config:
            self.y = config['y']

    def on(self, brightness=255, fade_ms=0, start_brightness=None,
           priority=0, cache=True, force=False):
        """Turns on this matrix light.

        Args:
            brightness: How bright this light should be, as an int between 0
                and 255. 0 is off. 255 is full on. Note that intermediary
                values are not yet implemented, so 0 is off, anything from
                1-255 is full on.
            fade_ms: Not yet implemented
            start_brightness: Not yet implemented.
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

        self.state['brightness'] = brightness
        self.state['priority'] = priority

        if cache:
            self.cache['brightness'] = brightness
            self.cache['priority'] = priority

        self.hw_driver.on(brightness, fade_ms, start_brightness)

    def off(self, fade_ms=0, priority=0, cache=True, force=False):
        self.on(brightness=0, fade_ms=fade_ms, priority=priority, cache=cache,
                force=force)
        """Turns this light off.

        Args:
            fade_ms: Not yet implemented
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