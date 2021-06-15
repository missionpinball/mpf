"""Contains the base classes for spinners."""

from mpf.core.enable_disable_mixin import EnableDisableMixinSystemWideDevice

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.exceptions.config_file_error import ConfigFileError


MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.driver import Driver           # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor(_active="active", _idle="idle")
class Spinner(EnableDisableMixinSystemWideDevice, SystemWideDevice):

    """Represents a spinner or spinner group in a pinball machine.

    Args: Same as the `Target` parent class
    """

    config_section = 'spinners'
    collection = 'spinners'
    class_label = 'spinner'

    __slots__ = [ "_active_ms", "_active", "_idle", "delay", "_tags"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialise drop target."""
        self._tags = None
        self._active = False
        self._idle = True
        self._active_ms = None
        super().__init__(machine, name)
        self.delay = DelayManager(machine)


    async def _initialize(self):
        await super()._initialize()
        # Cache this value because it's used a lot in rapid succession
        self._active_ms = self.config['active_ms']
        # can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_4',
                                        self._register_switch_handlers, priority=1)

    def _register_switch_handlers(self, **kwargs):
        del kwargs
        # register for notification of switch state
        # this is in addition to the parent since drop targets track
        # self.complete in separately

        self.info_log("Generating switch handlers: {}".format(self.config['switch']))
        for switch in self.config['switches']:
            callback_kwargs = { "tag": self._tags[switch] } if self._tags else None
            self.machine.switch_controller.add_switch_handler_obj(
                switch,
                self._update_state_from_switch, 1, callback_kwargs=callback_kwargs)

    def _update_state_from_switch(self, reconcile=False, **kwargs):
        self.info_log("Updating switch with kwargs {}".format(kwargs))
        tag = kwargs.get('tag')
        if not self._active:
            self.machine.events.post("spinner_{}_active".format(self.name))
            if tag:
                self.machine.events.post("spinner_{}_{}_hit".format(self.name, tag))
            self._active = True
            self._idle = False
        self.machine.events.post("spinner_{}_hit".format(self.name))
        if tag:
            self.machine.events.post("spinner_{}_{}_hit".format(self.name, tag))
        self.delay.clear()
        self.delay.add(self._active_ms, self._deactivate)

    def _deactivate(self, **kwargs):
        del kwargs
        self.machine.events.post("spinner_{}_inactive".format(self.name))
        self._active = False
        if self.config['idle_ms']:
            self.delay.add(self.config['idle_ms'], self._on_idle)
        else:
            self._idle = True

    def _on_idle(self, **kwargs):
        del kwargs
        self.machine.events.post("spinner_{}_idle".format(self.name))
        self._idle = True

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None):
        """Validate and parse shot config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        for switch in config['switch']:
            if switch not in config['switches']:
                config['switches'].append(switch)

        if config['switch_tags']:
            if len(config['switch_tags']) != len(config['switches']):
                raise ConfigFileError("Spinner switch_tags must be the same number as switches")
            self._tags = dict(zip(config['switches'], config['switch_tags']))
            self.info_log("built a list of tags! {}".format(self._tags))

        return config