""" Transfer a ball between two playfields. E.g. lower to upper playfield via a
ramp"""

from mpf.core.device import Device


class PlayfieldTransfer(Device):
    config_section = 'playfield_transfers'
    collection = 'playfield_transfers'
    class_label = 'playfield_transfer'

    def __init__(self, machine, name, config=None, validate=True):
        super().__init__(machine, name, config, validate=validate)

        self.machine.events.add_handler('init_phase_2',
                                        self.configure_switch)

        # load target playfield
        self.target = self.config['eject_target']
        self.source = self.config['captures_from']

    def configure_switch(self):
        self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['ball_switch'].name,
                callback=self._ball_went_through,
                state=1, ms=0)

    def _ball_went_through(self):
        self.log.debug("Ball went from %s to %s", self.source.name,
                       self.target.name)

        # source playfield is obviously active
        # we will continue using a callback to keep the ball count sane
        # (otherwise it may go to -1 during the next event)
        self.machine.events.post('sw_' + self.source.name + '_active',
                                 callback=self._ball_went_through2)

    # used as callback in _ball_went_through
    def _ball_went_through2(self):
        # trigger remove ball from source playfield
        self.machine.events.post(
            'balldevice_captured_from_' + self.source.name,
            balls=1)

        # inform target playfield about incomming ball
        self.machine.events.post(
            'balldevice_' + self.name + '_ball_eject_attempt',
            balls=1,
            target=self.target,
            timeout=0,
            callback=self._ball_went_through3)

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

    # used as callback in _ball_went_through3
    def _ball_went_through4(self, balls, target):
        del balls
        del target
        # since we confirmed eject target playfield has to be active
        self.machine.events.post('sw_' + self.target.name + '_active')
