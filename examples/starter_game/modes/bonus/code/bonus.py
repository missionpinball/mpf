from mpf.core.mode import Mode


class Bonus(Mode):

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.bonus_score = 0

    def mode_init(self):
        self.machine.events.add_handler('player_add_success',
                                        self.player_add)

    def player_add(self, player, **kwargs):
        del kwargs
        player['bonus_multiplier'] = 1

    def mode_start(self, **kwargs):
        del kwargs
        if self.machine.game.tilted:
            self.stop()

        self.bonus_score = 0
        self.bonus_start()

    def bonus_start(self):
        self.machine.events.post('bonus_start')
        self.delay.add(name='bonus', ms=500, callback=self.slings)

    def slings(self):
        self.machine.events.post('bonus_slings')
        self.bonus_score += self.player['slings'] * 100
        self.delay.add(name='bonus', ms=500, callback=self.total_hits)

    def total_hits(self):
        self.machine.events.post('bonus_hits')
        self.bonus_score += self.player['hits'] * 50
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
