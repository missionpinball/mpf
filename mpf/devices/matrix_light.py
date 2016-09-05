"""Contains the MatrixLight class."""

from operator import itemgetter

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.settings_controller import SettingEntry
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("_brightness", "_corrected_brightness")
class MatrixLight(SystemWideDevice):

    """Represents a light connected to a traditional lamp matrix in a pinball machine.

    This light could be an incandescent lamp or a replacement single-color
    LED. The key is that they're connected up to a lamp matrix.
    """

    config_section = 'matrix_lights'
    collection = 'lights'
    class_label = 'light'
    machine = None

    lights_to_update = set()
    lights_to_fade = set()
    _updater_task = None

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Initialise lights.

        Args:
            machine: MachineController object
        """
        cls.machine = machine
        cls.lights_to_fade = set()
        cls.lights_to_update = set()

        machine.validate_machine_config_section('matrix_light_settings')

        cls._updater_task = machine.clock.schedule_interval(
            cls.update_matrix_lights, 1 / machine.config['mpf']['default_matrix_light_hw_update_hz'])

        machine.mode_controller.register_stop_method(cls.mode_stop)

        machine.settings.add_setting(SettingEntry("brightness", "Brightness", 100, "brightness", 1.0,
                                                  {0.25: "25%", 0.5: "50%", 0.75: "75%", 1.0: "100% (default)"}))

    @classmethod
    def update_matrix_lights(cls, dt):
        """Write changed lights to hardware.

        Args:
            dt: time since last call
        """
        for light in list(MatrixLight.lights_to_fade):
            if light.fade_in_progress:
                light.fade_task(dt)

        # called periodically (default at the end of every frame) to actually
        # write the new light states to the hardware
        if MatrixLight.lights_to_update:
            for light in MatrixLight.lights_to_update:
                light.update_hw_light()

            MatrixLight.lights_to_update = set()

    @classmethod
    def mode_stop(cls, mode: Mode):
        """Remove all mode entries from stack.

        Args:
            mode: Mode which was removed
        """
        for light in cls.machine.lights:
            light.remove_from_stack_by_mode(mode)

    def __init__(self, machine, name):
        """Initialise light."""
        self.hw_driver = None
        self._brightness = 0
        self._corrected_brightness = 0
        super().__init__(machine, name)

        self.x = None
        self.y = None

        self.fade_in_progress = False
        self.default_fade_ms = None

        self.registered_handlers = list()

        self.stack = list()
        """A list of dicts which represents different commands that have come
        in to set this light to a certain brightness (and/or fade). Each entry
        in the list contains the following key/value pairs:

        priority: The relative priority of this brightness command. Higher
            numbers take precedent, and the highest priority entry will be the
            command that's currently active. In the event of a tie,
            whichever entry was added last wins (based on 'start_time' below).
        start_time: The clock time when this command was added. Primarily used
            to calculate fades, but also used as a tie-breaker for multiple
            entries with the same priority.
        start_brightness: Brightness this light when this command came in.
        dest_time: Clock time that represents when a fade (from
            start_brightness to dest_brightness ) will be done. If this is 0,
            that means there is no fade. When a fade is complete, this value is
             reset to 0.
        dest_brightness: Brightness of the destination this light is fading
            to. If a command comes in with no fade, then this will be the same
            as the 'brightness' below.
        brightness: The current brightness of the light based on this command.
            (0-255) This value is updated automatically as fades progress, and
            it's the value that's actually written to the hardware.
        key: An arbitrary unique identifier to keep multiple entries in the
            stack separate. If a new brightness command comes in with a key
            that already exists for an entry in the stack, that entry will be
            replaced by the new entry. The key is also used to remove entries
            from the stack (e.g. when shows or modes end and they want to
            remove their commands from the light).
        mode: Optional mode where the brightness was set. Used to remove
            entries when a mode ends.

        """

    def _initialize(self):
        self.load_platform_section('matrix_lights')

        self.hw_driver = self.platform.configure_matrixlight(self.config)

        if self.config['fade_ms'] is not None:
            self.default_fade_ms = self.config['fade_ms']
        elif self.machine.config['matrix_light_settings']:
            self.default_fade_ms = (
                self.machine.config['matrix_light_settings']['default_light_fade_ms'])
        else:
            self.default_fade_ms = 0

        if 'x' in self.config:
            self.x = self.config['x']

        if 'y' in self.config:
            self.y = self.config['y']

    # pylint: disable-msg=too-many-arguments
    def on(self, brightness=255, fade_ms=None, priority=0, key=None, mode=None,
           **kwargs):
        """Turn light on.

        Add or updates a brightness entry in this lights's stack, which is
        how you tell this light how bright you want it to be.

        Args:
            brightness: How bright this light should be, as an int between 0
                and 255. 0 is off. 255 is full on. Note that matrix lights in
                older (even WPC) machines had slow matrix update speeds, and
                effective brightness levels will be far less than 255.
            fade_ms: Int of the number of ms you want this light to fade to the
                brightness in. A value of 0 means it's instant. A value of
                None (the default) means that it will use this lights's and/or
                the machine's default fade_ms setting.
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
                brightness. When a mode ends, entries from the stack with that
                mode will automatically be removed.
            **kwargs: Not used. Only included so this method can be used as
                an event callback since events could pass random kwargs.
        """
        del kwargs

        if self.debug:
            self.log.debug("Received on() command. brightness: %s, fade_ms: %s"
                           "priority: %s, key: %s", brightness, fade_ms,
                           priority, key)

        if fade_ms is None:
            fade_ms = self.default_fade_ms

        if priority < self._get_priority_from_key(key):
            if self.debug:
                self.log.debug("Incoming priority is lower than an existing "
                               "stack item with the same key. Not adding to "
                               "stack.")

            return

        self._add_to_stack(brightness, fade_ms, priority, key, mode)

    # pylint: disable-msg=too-many-arguments
    def _add_to_stack(self, brightness, fade_ms, priority, key, mode):
        curr_brightness = self.get_brightness()

        self.remove_from_stack_by_key(key)

        if fade_ms:
            new_brightness = curr_brightness
            dest_time = self.machine.clock.get_time() + (fade_ms / 1000)
        else:
            new_brightness = brightness
            dest_time = 0

        self.stack.append(dict(priority=priority,
                               start_time=self.machine.clock.get_time(),
                               start_brightness=curr_brightness,
                               dest_time=dest_time,
                               dest_brightness=brightness,
                               brightness=new_brightness,
                               key=key,
                               mode=mode))

        self.stack.sort(key=itemgetter('priority', 'start_time'), reverse=True)

        if self.debug:
            self.log.debug("+-------------- Adding to stack ----------------+")
            self.log.debug("priority: %s", priority)
            self.log.debug("start_time: %s", self.machine.clock.get_time())
            self.log.debug("start_brightness: %s", curr_brightness)
            self.log.debug("dest_time: %s", dest_time)
            self.log.debug("dest_brightness: %s", brightness)
            self.log.debug("brightness: %s", new_brightness)
            self.log.debug("key: %s", key)

        MatrixLight.lights_to_update.add(self)

    def clear_stack(self):
        """Remove all entries from the stack and resets this light to 'off'."""
        self.stack[:] = []

        if self.debug:
            self.log.debug("Clearing Stack")

        MatrixLight.lights_to_update.add(self)

    def remove_from_stack_by_key(self, key):
        """Remove a group of brightness settings from the stack.

        Args:
            key: The key of the settings to remove (based on the 'key'
                parameter that was originally passed to the brightness() method.)

        This method triggers a light update, so if the highest priority settings
        were removed, the light will be updated with whatever's below it. If no
        settings remain after these are removed, the light will turn off.
        """
        if self.debug:
            self.log.debug("Removing key '%s' from stack", key)

        self.stack[:] = [x for x in self.stack if x['key'] != key]
        MatrixLight.lights_to_update.add(self)

    def remove_from_stack_by_mode(self, mode: Mode):
        """Remove a group of brightness settings from the stack.

        Args:
            mode: Mode which was removed

        This method triggers a light update, so if the highest priority settings
        were removed, the light will be updated with whatever's below it. If no
        settings remain after these are removed, the light will turn off.
        """
        if self.debug:
            self.log.debug("Removing mode '%s' from stack", mode)

        self.stack[:] = [x for x in self.stack if x['mode'] != mode]
        MatrixLight.lights_to_update.add(self)

    def get_brightness(self):
        """Return an RGBColor() instance of the 'color' setting of the highest color setting in the stack.

        This is usually the same color as the
        physical LED, but not always (since physical LEDs are updated once per
        frame, this value could vary.

        Also note the color returned is the "raw" color that does has not had
        the color correction profile applied.
        """
        try:
            return self.stack[0]['brightness']
        except IndexError:
            return 0

    def _get_priority_from_key(self, key):
        try:
            return [x for x in self.stack if x['key'] == key][0]['priority']
        except IndexError:
            return 0

    def _gamma_correct(self, brightness):
        factor = self.machine.get_machine_var("brightness")
        if not factor:
            return brightness
        else:
            return factor * brightness

    def update_hw_light(self):
        """Set brightness to hardware platform.

        Physically updates the light hardware object based on the
        'brightness' setting of the highest priority setting from the stack.

        This method is automatically called whenever a brightness change has been
        made (including when fades are active).
        """
        if not self.stack:
            self.off()

        # if there's a current fade, but the new command doesn't have one
        if not self.stack[0]['dest_time'] and self.fade_in_progress:
            self._stop_fade_task()

        # If the new command has a fade, but the fade task isn't running
        if self.stack[0]['dest_time'] and not self.fade_in_progress:
            self._setup_fade()

        # If there's no current fade and no new fade, or a current fade and new
        # fade
        else:
            self._corrected_brightness = self._gamma_correct(self.stack[0]['brightness'])
            self.hw_driver.on(self._corrected_brightness)
            self._brightness = self.stack[0]['brightness']

            if self.registered_handlers:
                # Handlers are not sent brightness corrected brightnesss
                # todo make this a config option?
                for handler in self.registered_handlers:
                    handler(light_name=self.name,
                            brightness=self.stack[0]['brightness'])

    def off(self, fade_ms=0, priority=0, key=None, mode=None, **kwargs):
        """Turn this light off.

        Args:
            fade_ms: Int of the number of ms you want this light to fade to the
                brightness in. A value of 0 means it's instant. A value of
                None (the default) means that it will use this lights's and/or
                the machine's default fade_ms setting.
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
                brightness. When a mode ends, entries from the stack with that
                mode will automatically be removed.
            **kwargs: Not used. Only included so this method can be used as
                an event callback since events could pass random kwargs.
        """
        del kwargs
        self.on(brightness=0, fade_ms=fade_ms, priority=priority, key=key,
                mode=mode)

    def add_handler(self, callback):
        """Register a handler to be called when this light changes state.

        Args:
            callback: Monitor callback to add
        """
        self.registered_handlers.append(callback)

    def remove_handler(self, callback=None):
        """Remove a handler from the list of registered handlers.

        Args:
            callback: Monitor callback to remove
        """
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

        MatrixLight.lights_to_fade.add(self)

    def fade_task(self, dt):
        """Update the brightness depending on the time for a fade.

        Args:
            dt: time since last call
        """
        del dt

        # not sure why this is needed, but sometimes the fade task tries to
        # run even though self.fade_in_progress is False. Maybe
        # clock.unschedule doesn't happen right away?
        if not self.fade_in_progress:
            return

        try:
            brightness_settings = self.stack[0]
        except IndexError:
            self._stop_fade_task()
            return

        # todo
        if not brightness_settings['dest_time']:
            return

        # figure out the ratio of how far along we are
        try:
            ratio = ((self.machine.clock.get_time() -
                      brightness_settings['start_time']) /
                     (brightness_settings['dest_time'] -
                      brightness_settings['start_time']))
        except ZeroDivisionError:
            ratio = 1.0

        if self.debug:
            self.log.debug("Fade task, ratio: %s", ratio)

        if ratio >= 1.0:  # fade is done
            self._end_fade()
            brightness_settings['brightness'] = (
                brightness_settings['dest_brightness'])
        else:
            brightness_settings['brightness'] = (
                brightness_settings['start_brightness'] +
                int((brightness_settings['dest_brightness'] -
                    brightness_settings['start_brightness']) * ratio))

        MatrixLight.lights_to_update.add(self)

    def _end_fade(self):
        """Stop the fade and instantly sets the light to its destination brightness."""
        self._stop_fade_task()
        self.stack[0]['dest_time'] = 0

    def _stop_fade_task(self):
        """Stop the fade task. Light is left in whatever state it was in."""
        self.fade_in_progress = False
        MatrixLight.lights_to_fade.remove(self)

        if self.debug:
            self.log.debug("Stopping fade task")
