"""Transfer a ball between two playfields.

E.g. lower to upper playfield via a ramp.
"""
from mpf.core.events import event_handler
from mpf.core.system_wide_device import SystemWideDevice


class PlayfieldTransfer(SystemWideDevice):

    """Device which move a ball from one playfield to another."""

    config_section = 'playfield_transfers'
    collection = 'playfield_transfers'
    class_label = 'playfield_transfer'

    __slots__ = ["target", "source"]

    def __init__(self, machine, name):
        """Initialise playfield transfer."""
        self.target = None
        self.source = None
        super().__init__(machine, name)

    async def _initialize(self):
        await super()._initialize()
        if self.config['ball_switch']:
            self.machine.events.add_handler('init_phase_3',
                                            self._configure_switch)

        # load target playfield
        self.target = self.config['eject_target']
        self.source = self.config['captures_from']

    def _configure_switch(self, **kwargs):
        del kwargs
        self.machine.switch_controller.add_switch_handler_obj(
            switch=self.config['ball_switch'],
            callback=self.transfer,
            state=1, ms=0)

    @event_handler(1)
    def event_transfer(self, **kwargs):
        """Event handler for transfer event."""
        del kwargs
        self.transfer()

    def transfer(self):
        """Transfer a ball to the target playfield."""
        self.debug_log("Ball went from %s to %s", self.source.name,
                       self.target.name)

        # source playfield is obviously active
        # we will continue using a callback to keep the ball count sane
        # (otherwise it may go to -1 during the next event)
        self.machine.events.post('sw_' + self.source.name + '_active',
                                 callback=self._ball_went_through2, balls=1)
        # event docstring in playfield module.

        self.machine.events.post('playfield_transfer_{}_ball_transferred'.format(self.name),
                                 source=self.source, target=self.target)
        '''event: playfield_transfer_(playfield_transfer)_ball_transferred
        desc: The playfield_transfer called (playfield_transfer) transferred a ball from playfield (source) to
        playfield (target).

        args:
        source: The source playfield.
        target: The target playfield.
        '''

    # used as callback in _ball_went_through
    def _ball_went_through2(self, **kwargs):
        del kwargs
        # trigger remove ball from source playfield
        self.machine.events.post(
            'balldevice_captured_from_' + self.source.name,
            balls=1)
        # event docstring covered elsewhere

        # inform target playfield about incoming ball
        self.machine.events.post(
            'balldevice_' + self.name + '_ejecting_ball',
            balls=1,
            target=self.target,
            timeout=0,
            callback=self._ball_went_through3)
        # event docstring covered elsewhere

    # used as callback in _ball_went_through2
    def _ball_went_through3(self, balls, target, timeout):
        del balls
        del target
        del timeout
        # promise (and hope) that it actually goes there
        self.machine.events.post(
            'balldevice_' + self.name + '_ball_eject_success',
            balls=1,
            target=self.target,
            callback=self._ball_went_through4)
        self.target.available_balls += 1
        # event docstring covered elsewhere

    # used as callback in _ball_went_through3
    def _ball_went_through4(self, balls, target):
        del balls
        del target
        # since we confirmed eject target playfield has to be active
        self.machine.events.post('sw_' + self.target.name + '_active')
        # event docstring covered elsewhere
