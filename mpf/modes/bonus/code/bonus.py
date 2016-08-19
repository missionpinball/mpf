"""Bonus mode for MPF."""
from mpf.core.mode import Mode


class Bonus(Mode):

    """Bonus mode for MPF.

    Give a player bonus for his achievements. But only if the machine is not tilted.
    """

    def __init__(self, machine, config, name, path):
        """Initialise bonus mode."""
        super().__init__(machine, config, name, path)
        self.bonus_score = None
        self.settings = config.get("mode_settings")
        self.display_delay = self.settings.get("display_delay_ms", 2000)
        self.bonus_entries = self.settings.get("bonus_entries", [])
        self.bonus_iterator = None

    def mode_start(self, **kwargs):
        """Start the bonus mode."""
        # no bonus when machine is tilted
        if self.machine.game.tilted:
            # reset all scores because they should be voided
            self._reset_all_scores()
            # and stop mode
            self.stop()
            return

        self.bonus_score = 0
        self.bonus_iterator = iter(self.bonus_entries)

        # post start event
        self.machine.events.post('bonus_start')
        self._bonus_next_item()

    def _reset_all_scores(self):
        """Reset score entries without scoring them.

        We keep the permanent entries.
        """
        for entry in self.bonus_entries:
            if entry['reset_player_score_entry']:
                self.player.vars[entry['player_score_entry']] = 0

    def _bonus_next_item(self):
        try:
            entry = next(self.bonus_iterator)
        except StopIteration:
            self._subtotal()
            return

        hits = self.player.vars.get(entry['player_score_entry'], 0)
        score = entry['score'] * hits
        self.bonus_score += score
        self.machine.events.post(entry['event'], score=score, bonus_score=self.bonus_score, hits=hits)
        if entry['reset_player_score_entry']:
            self.player.vars[entry['player_score_entry']] = 0

        self.delay.add(name='bonus', ms=self.display_delay, callback=self._bonus_next_item)

    def _subtotal(self):
        self.machine.events.post('bonus_subtotal', score=self.bonus_score)
        self.delay.add(name='bonus', ms=self.display_delay, callback=self._do_multiplier)

    def _do_multiplier(self):
        multiplier = self.player.vars.get("bonus_multiplier", 1)
        self.machine.events.post('bonus_multiplier', multiplier=multiplier)
        self.bonus_score *= multiplier
        self.delay.add(name='bonus', ms=self.display_delay, callback=self._total_bonus)

    def _total_bonus(self):
        self.player.score += self.bonus_score
        self.machine.events.post('bonus_total', score=self.bonus_score)
        self.delay.add(name='bonus', ms=self.display_delay, callback=self._end_bonus)

    def _end_bonus(self):
        if not self.settings['keep_multiplier']:
            self.player.bonus_multiplier = 1
        self.stop()
