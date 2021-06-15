"""Contains the base classes for spinners."""

from mpf.core.enable_disable_mixin import EnableDisableMixinSystemWideDevice

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.exceptions.config_file_error import ConfigFileError


MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor(_active="active", _idle="idle")
class Spinner(EnableDisableMixinSystemWideDevice, SystemWideDevice):

    """Represents a spinner or spinner group in a pinball machine."""

    config_section = 'spinners'
    collection = 'spinners'
    class_label = 'spinner'

    __slots__ = ["_active_ms", "_active", "_idle", "delay", "_tags"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialise spinner device."""
        super().__init__(machine, name)
        self._tags = None
        self._active = False
        self._idle = True
        self._active_ms = None
        self.delay = DelayManager(machine)
        self.enabled = True  # Default to enabled

    async def _initialize(self):
        await super()._initialize()
        # Cache this value because it's used a lot in rapid succession
        self._active_ms = self.config['active_ms']
        # Can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_4',
                                        self._register_switch_handlers, priority=1)

    def _register_switch_handlers(self, **kwargs):
        del kwargs

        for switch in self.config['switches']:
            callback_kwargs = {"tag": self._tags[switch]} if self._tags else None
            # register for notification of switch active state
            self.machine.switch_controller.add_switch_handler_obj(
                switch,
                self._update_state_from_switch, 1, callback_kwargs=callback_kwargs)

    def _update_state_from_switch(self, **kwargs):
        if not self.enabled:
            return
        tag = kwargs.get('tag')
        if not self._active:
            self.machine.events.post("spinner_{}_active".format(self.name))
            if tag:
                self.machine.events.post("spinner_{}_{}_active".format(self.name, tag))
            self._active = True
            self._idle = False
        self.machine.events.post("spinner_{}_hit".format(self.name))
        if tag:
            self.machine.events.post("spinner_{}_{}_hit".format(self.name, tag))
        self.delay.clear()
        self.delay.add(self._active_ms, self._deactivate)

    def _deactivate(self, **kwargs):
        """Post an 'inactive' event after no switch hits for the active_ms duration."""
        del kwargs
        self.machine.events.post("spinner_{}_inactive".format(self.name))
        self._active = False
        if self.config['idle_ms']:
            self.delay.add(self.config['idle_ms'], self._on_idle)
        else:
            self._idle = True

    def _on_idle(self, **kwargs):
        """Post an 'idle' event if the spinner has been inactive for the idle_ms duration."""
        del kwargs
        self.machine.events.post("spinner_{}_idle".format(self.name))
        self._idle = True

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None):
        """Validate and parse spinner config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        for switch in config['switch']:
            if switch not in config['switches']:
                config['switches'].append(switch)

        if config['switch_tags']:
            if len(config['switch_tags']) != len(config['switches']):
                raise ConfigFileError("Spinner switch_tags must be the same number as switches", 1, self.name)
            self._tags = dict(zip(config['switches'], config['switch_tags']))

        return config

    @property
    def active(self):
        """Return whether the spinner is actively spinning."""
        return self._active

    @property
    def idle(self):
        """Return whether the spinner is idle."""
        return self._idle
