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

    __slots__ = ["hits", "_active_ms", "_active", "_idle", "_event_buffer_ms", "delay"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialize spinner device."""
        super().__init__(machine, name)
        self._active = False
        self._idle = True
        self._active_ms = None
        self._event_buffer_ms = None
        self.hits = None
        self.delay = DelayManager(machine)
        self.enabled = True  # Default to enabled

        self.configure_logging(f'Spinner.{name}')

    async def _initialize(self):
        await super()._initialize()
        self.hits = 0
        # Cache this value because it's used a lot in rapid succession
        self._active_ms = self.config['active_ms']
        if self.config['max_events_per_second'] > 0:
            self._event_buffer_ms = (1 / self.config['max_events_per_second']) * 1000
            self.log.debug("Configured event buffer for %s", self._event_buffer_ms)
        # Can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_4',
                                        self._register_switch_handlers, priority=1)

    def _register_switch_handlers(self, **kwargs):
        del kwargs

        labels = dict(zip(self.config['switches'], self.config['labels'])) if self.config['labels'] else None
        for switch in self.config['switches']:
            callback_kwargs = {"label": labels[switch]} if labels else None
            # register for notification of switch active state
            self.machine.switch_controller.add_switch_handler_obj(
                switch,
                self._update_state_from_switch, 1, callback_kwargs=callback_kwargs)

    def _update_state_from_switch(self, **kwargs):
        if not self.enabled:
            return
        label = kwargs.get("label")
        if not self._active:
            self.machine.events.post("spinner_{}_active".format(self.name), label=label)
            '''event: spinner_(name)_active
            desc: The idle spinner (name) was just hit and became active.

            This event will post whenever a spinner switch is hit and the spinner
            is not already active.

            args:
            label: The label of the switch that triggered the activation
            '''
            if label:
                self.machine.events.post("spinner_{}_{}_active".format(self.name, label))
                '''event: spinner_(name)_(label)_active
                desc: The idle spinner (name) was just hit and became active.

                This event will post whenever a spinner switch is hit and the spinner
                is not already active, but only if labels are defined for the spinner.
                '''
            self._active = True
            self._idle = False
        self.hits += 1

        if not self._event_buffer_ms or not self.delay.check("event_buffer"):
            self._post_hit_event(label=label, last_hits=self.hits - 1)

    def _post_hit_event(self, **kwargs):
        last_hits = kwargs.get("last_hits", 0)
        self.log.debug("Buffer check has %s previous hits, current is %s", last_hits, self.hits)
        if last_hits and last_hits == self.hits:
            self.delay.remove("event_buffer")
            return

        label = kwargs.get("label")

        self.machine.events.post("spinner_{}_hit".format(self.name), hits=self.hits,
                                 change=self.hits - last_hits, label=label)
        '''event: spinner_(name)_hit
        desc: The spinner (name) was just hit.

        This event will post whenever a spinner switch is hit.

        args:
        hits: The number of switch hits the spinner has had since it became active
        label: The label of the switch that was hit
        '''
        if label:
            self.machine.events.post("spinner_{}_{}_hit".format(self.name, label),
                                     hits=self.hits, change=self.hits - last_hits)
            '''event: spinner_(name)_(label)_hit
            desc: The spinner (name) was just hit on the switch labelled (label).

            This event will post whenever a spinner switch is hit and labels
            are defined for the spinner
            '''
        self.delay.reset(self._active_ms, self._deactivate, "deactivate")

        if self._event_buffer_ms:
            self.delay.add(self._event_buffer_ms, self._post_hit_event, "event_buffer",
                           label=label, last_hits=self.hits)

    def _deactivate(self, **kwargs):
        """Post an 'inactive' event after no switch hits for the active_ms duration."""
        del kwargs
        self.machine.events.post("spinner_{}_inactive".format(self.name), hits=self.hits)
        '''event: spinner_(name)_inactive
        desc: The spinner (name) is no longer receiving hits

        This event will post whenever a spinner has not received hits and
        its active_ms has timed out.

        args:
        hits: The number of switch hits the spinner had while it was active
        '''
        self._active = False
        if self.config['idle_ms']:
            self.delay.reset(self.config['idle_ms'], self._on_idle, "idle")
            if self.config['reset_when_inactive']:
                self.hits = 0
        else:
            self._idle = True

    def _on_idle(self, **kwargs):
        """Post an 'idle' event if the spinner has been inactive for the idle_ms duration."""
        del kwargs
        self.machine.events.post("spinner_{}_idle".format(self.name), hits=self.hits)
        '''event: spinner_(name)_idle
        desc: The spinner (name) is now idle

        This event will post whenever a spinner has not received hits and
        its idle_ms has timed out. If no idle_ms is defined, this event
        will not post.

        args:
        hits: The number of switch hits the spinner had while it was active
        '''
        self.hits = 0
        self._idle = True

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None):
        """Validate and parse spinner config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        for switch in config['switch']:
            if switch not in config['switches']:
                config['switches'].append(switch)

        if config['labels'] and len(config['labels']) != len(config['switches']):
            raise ConfigFileError("Spinner labels must be the same number as switches", 1, self.name)

        return config

    @property
    def active(self):
        """Return whether the spinner is actively spinning."""
        return self._active

    @property
    def idle(self):
        """Return whether the spinner is idle."""
        return self._idle
