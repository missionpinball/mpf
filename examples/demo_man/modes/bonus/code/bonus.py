from mpf.core.mode import Mode


class Bonus(Mode):

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.bonus_score = 0

    def mode_start(self, **kwargs):
        del kwargs
        self.bonus_score = 0
        self.bonus_start()

    def bonus_start(self):
        self.machine.events.post('bonus_start')
        self.delay.add(name='bonus', ms=500, callback=self.total_ramps)

    def total_ramps(self):
        self.machine.events.post('bonus_ramps')
        self.bonus_score += self.player['ramps'] * 10000
        self.delay.add(name='bonus', ms=500, callback=self.total_modes)

    def total_modes(self):
        self.machine.events.post('bonus_modes')
        self.bonus_score += self.player['modes'] * 50000
        self.delay.add(name='bonus', ms=500, callback=self.subtotal)

    def subtotal(self):
        self.machine.events.post('bonus_subtotal', points=self.bonus_score)
        self.delay.add(name='bonus', ms=500, callback=self.do_multiplier)

    def do_multiplier(self):
        self.machine.events.post('bonus_multiplier')
        self.delay.add(name='bonus', ms=500, callback=self.total_bonus)

    def total_bonus(self):
        self.bonus_score *= self.player['bonus_multiplier']
        self.player['score'] += self.bonus_score
        self.machine.events.post('bonus_total', points=self.bonus_score)
        self.delay.add(name='bonus', ms=500, callback=self.end_bonus)

    def end_bonus(self):
        if not self.player['hold_bonus']:
            self.player['bonus_multiplier'] = 1
        else:
            self.player['hold_bonus'] = False

        self.stop()
