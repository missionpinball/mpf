"""Contains the Switch parent class."""
from typing import Optional, Dict, List

from functools import partial

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util
from mpf.core.platform import SwitchConfig
from mpf.devices.device_mixins import DevicePositionMixin
from mpf.exceptions.config_file_error import ConfigFileError

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface  # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.core.platform import SwitchPlatform    # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor("state", "recycle_jitter_count")
class Switch(SystemWideDevice, DevicePositionMixin):

    """A switch in a pinball machine."""

    config_section = 'switches'
    collection = 'switches'
    class_label = 'switch'

    __slots__ = ["hw_switch", "platform", "state", "hw_state", "invert", "recycle_secs", "recycle_clear_time",
                 "recycle_jitter_count", "_events_to_post", "last_change"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """initialize switch."""
        self.hw_switch = None   # type: Optional[SwitchPlatformInterface]
        self.platform = None    # type: Optional[SwitchPlatform]
        super().__init__(machine, name)

        self.state = 0
        """ The logical state of a switch. 1 = active, 0 = inactive. This takes
        into consideration the NC or NO settings for the switch."""
        self.hw_state = 0
        """ The physical hardware state of the switch. 1 = active,
        0 = inactive. This is what the actual hardware is reporting and does
        not consider whether a switch is NC or NO."""

        self.invert = 0

        self.recycle_secs = 0
        self.recycle_clear_time = None
        self.recycle_jitter_count = 0
        self._events_to_post = {0: [], 1: []}       # type: Dict[int, List[str]]
        self.last_change = -100000

        # register switch so other devices can add handlers to it
        self.machine.switch_controller.register_switch(self)

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Register handler for duplicate switch number checks."""
        machine.events.add_handler("init_phase_4",
                                   cls._check_duplicate_switch_numbers,
                                   machine=machine)

    def get_ms_since_last_change(self, current_time=None) -> int:
        """Get ms since last change.

        Will use the current time from clock if you do not pass it.
        """
        if current_time is None:
            current_time = self.machine.clock.get_time()
        return round((current_time - self.last_change) * 1000.0, 0)

    @staticmethod
    def _check_duplicate_switch_numbers(machine, **kwargs):
        del kwargs
        check_set = set()
        for switch in machine.switches.values():
            key = (switch.config['platform'], switch.hw_switch.number)
            if key in check_set:
                raise AssertionError(
                    "Duplicate switch number {} for switch {}".format(
                        switch.hw_switch.number, switch))

            check_set.add(key)

    def validate_and_parse_config(self, config, is_mode_config, debug_prefix: str = None):
        """Validate switch config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        platform = self.machine.get_platform_sections(
            'switches', getattr(config, "platform", None))
        platform.assert_has_feature("switches")
        config['platform_settings'] = platform.validate_switch_section(
            self, config.get('platform_settings', None))
        self._configure_device_logging(config)
        return config

    def _create_activation_event(self, event_str: str, state: int):
        if "|" in event_str:
            event, ev_time = event_str.split("|")
            ms = Util.string_to_ms(ev_time)
            self.machine.switch_controller.add_switch_handler_obj(
                switch=self,
                state=state,
                callback=self.machine.events.post,
                ms=ms,
                callback_kwargs={"event": event}
            )
        else:
            self._events_to_post[state].append(event_str)

    def _recycle_passed(self, state):
        self.recycle_clear_time = None
        # only post event if the switch toggled
        if self.state != state:
            self._post_events(self.state)

    def _post_events_with_recycle(self, state):
        # if recycle is ongoing do nothing
        if not self.recycle_clear_time:
            # calculate clear time
            self.recycle_clear_time = self.last_change + self.recycle_secs
            self.machine.clock.loop.call_at(self.recycle_clear_time, partial(self._recycle_passed, state))
            # post event
            self._post_events(state)

    def _post_events(self, state):
        for event in self._events_to_post[state]:
            if self._debug or self.machine.events.does_event_exist(event):
                self.machine.events.post(event)

    async def _initialize(self):
        await super()._initialize()
        self.platform = self.machine.get_platform_sections(
            'switches', self.config['platform'])

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_secs = self.config['ignore_window_ms'] / 1000.0

        config = SwitchConfig(name=self.name,
                              invert=self.invert,
                              debounce=self.config['debounce'])
        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Switch must have a number.", 1)

        try:
            self.hw_switch = self.platform.configure_switch(
                self.config['number'], config, self.config['platform_settings'])
        except AssertionError as e:
            raise ConfigFileError("Failed to configure switch {} in platform. See error above".format(self.name), 2,
                                  self.class_label) from e

        if self.recycle_secs:
            self.add_handler(state=1, callback=self._post_events_with_recycle, callback_kwargs={"state": 1})
            self.add_handler(state=0, callback=self._post_events_with_recycle, callback_kwargs={"state": 0})
        else:
            self.add_handler(state=1, callback=self._post_events, callback_kwargs={"state": 1})
            self.add_handler(state=0, callback=self._post_events, callback_kwargs={"state": 0})

        if self.machine.config['mpf']['auto_create_switch_events']:
            self._create_activation_event(
                self.machine.config['mpf']['switch_event_active'].replace(
                    '%', self.name), 1)
            '''event: (name)_active
            desc: Posted when this switch becomes active.
            Note that this will only be posted if there is an event handler for it or if debug is set to True on this
            switch for performance reasons.
            '''
            self._create_activation_event(
                self.machine.config['mpf']['switch_event_inactive'].replace(
                    '%', self.name), 0)
            '''event: (name)_inactive
            desc: Posted when this switch becomes inactive.
            Note that this will only be posted if there is an event handler for it or if debug is set to True on this
            switch for performance reasons.
            '''

        for tag in self.tags:
            self._create_activation_event(
                self.machine.config['mpf']['switch_tag_event'].replace(
                    '%', tag), 1)
            '''event: sw_(tag)
            desc: Posted when a switch with this tag becomes active.
            Note that this will only be posted if there is an event handler for it or if debug is set to True on this
            switch for performance reasons.
            '''
            self._create_activation_event(
                self.machine.config['mpf']['switch_tag_event'].replace(
                    '%', tag) + "_active", 1)
            '''event: sw_(tag)_active
            desc: Posted when a switch with this tag becomes active.
            Note that this will only be posted if there is an event handler for it or if debug is set to True on this
            switch for performance reasons.
            '''
            self._create_activation_event(
                self.machine.config['mpf']['switch_tag_event'].replace(
                    '%', tag) + "_inactive", 0)
            '''event: sw_(tag)_inactive
            desc: Posted when a switch with this tag becomes inactive.
            Note that this will only be posted if there is an event handler for it or if debug is set to True on this
            switch for performance reasons.
            '''

        for event in Util.string_to_event_list(
                self.config['events_when_activated']):
            self._create_activation_event(event, 1)

        for event in Util.string_to_event_list(
                self.config['events_when_deactivated']):
            self._create_activation_event(event, 0)

    # pylint: disable-msg=too-many-arguments
    def add_handler(self, callback, state=1, ms=0, return_info=False,
                    callback_kwargs=None):
        """Add switch handler (callback) for this switch which is called when this switch state changes.

        Note that this method just calls the
        :doc:`Switch Controller's <self.machine.switch_controller>`
        ``add_switch_handler()`` method behind the scenes.

        Args:
        ----
            callback: A callable method that will be called when the switch
                state changes.
            state: The state that the switch which change into which triggers
                the callback to be called. Values are 0 or 1, with 0 meaning
                the switch changed to inactive, and 1 meaning the switch
                changed to an active state.
            ms: How many milliseconds the switch needs to be in the new state
                before the callback is called. Default is 0 which means that
                the callback will be called immediately. You can use this
                setting as a form of software debounce, as the switch needs to
                be in the state consistently before the callback is called.
            return_info: If True, the switch controller will pass the
                parameters of the switch handler as arguments to the callback,
                including switch_name, state, and ms.
            callback_kwargs: Additional kwargs that will be passed with the
                callback.
        """
        return self.machine.switch_controller.add_switch_handler_obj(
            self, callback, state, ms, return_info, callback_kwargs)

    def remove_handler(self, callback, state=1, ms=0):
        """Remove switch handler for this switch."""
        return self.machine.switch_controller.remove_switch_handler_obj(
            self, callback, state, ms)
