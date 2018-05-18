from mpf.core.mode_device import ModeDevice

@DeviceMonitor("state")
class LogicBlock(ModeDevice):

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize state device."""
        super().__init__(machine, name)
        self._state = None          # type: bool

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        if self.config['start_enabled'] is not None:
            # use setting of start_enabled
            self._state = self.config['start_enabled']
        else:
            # if start_enabled is None enable only if there are no enable_events
            self._state = not self.config['enable_events']


