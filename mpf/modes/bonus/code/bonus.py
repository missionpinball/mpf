"""Bonus mode for MPF."""
from mpf.core.mode import Mode


class Bonus(Mode):

    """Bonus mode for MPF.

    Give a player bonus for their achievements, but only if the machine is not
    tilted.
    """

    __slots__ = ["bonus_score", "settings", "display_delay", "bonus_entries", "bonus_iterator"]

    def __init__(self, *args, **kwargs):
        """Initialize bonus mode."""
        super().__init__(*args, **kwargs)
        self.bonus_score = None

        self.settings = self.machine.config_validator.validate_config(
            'bonus_mode_settings', self.config.get("mode_settings"))

        self.display_delay = self.settings["display_delay_ms"]
        self.bonus_entries = self.settings["bonus_entries"]
        self.bonus_iterator = None

    def mode_start(self, **kwargs):
        """Start the bonus mode and setup all handlers."""
        if not self.bonus_entries:
            raise ValueError(
                "Bonus mode started, but `bonus_entries` is not configured.")

        if not self.machine.game:
            self.debug_log("Game is not running. Skipping bonus.")
            self.stop()
            return

        if self.machine.game.tilted:
            self.debug_log("Machine is tilted. Skipping bonus.")
            self._reset_all_scores()
            self.stop()
            return

        self.bonus_score = 0
        self.bonus_iterator = iter(self.bonus_entries)
        self.display_delay = self.settings["display_delay_ms"]
        self.machine.events.post('bonus_start')
        '''event: bonus_start

        desc: The end-of-ball bonus is starting. You can use this event in
        your slide player to trigger the bonus intro slide. If the game has
        tilted, this event will not be posted.

        '''
        self.delay.add(name='bonus', ms=self.display_delay,
                       callback=self._bonus_next_item)

        if self.settings["hurry_up_event"]:
            self.add_mode_event_handler(self.settings['hurry_up_event'],
                                        self.hurry_up)

        if self.settings["end_bonus_event"]:
            self.add_mode_event_handler(self.settings['end_bonus_event'],
                                        self._end_bonus)

    def hurry_up(self, **kwargs):
        """Change the slide display delay to the "hurry up" setting.

        This is typically used with a flipper cancel event to hurry up the
        bonus display when the player hits both flippers.
        """
        del kwargs
        self.display_delay = self.settings["hurry_up_delay_ms"]
        self.delay.run_now('bonus')

    def _reset_all_scores(self):
        """Reset score entries without scoring them.

        We keep the permanent entries.
        """
        self.debug_log("Resetting player_score_entries that are set to reset.")
        for entry in self.bonus_entries:
            if entry['reset_player_score_entry']:
                self.player.vars[entry['player_score_entry']] = 0

    def _bonus_next_item(self):

        try:
            entry = next(self.bonus_iterator)
        except StopIteration:
            self._subtotal()
            return

        # Because all bonus events are 'bonus_entry' with a name arg, the
        # following names are reserved for end-of-bonus behavior.
        assert entry not in ["subtotal", "multiplier", "total"], "Bonus entry cannot be reserved word '%s'" % entry

        # If a player_score_entry is provided, use player getattr to get a
        # fallback value of zero if the variable is not set. Otherwise
        # use 1 as the multiplier for non-player-score bonuses.
        hits = self.player[entry['player_score_entry']] if entry['player_score_entry'] else 1
        score = entry['score'].evaluate([]) * hits

        if (not score and entry['skip_if_zero']) or (score < 0 and entry['skip_if_negative']):
            self.info_log("Skipping bonus entry '%s' because its value is 0",
                          entry['entry'])
            self._bonus_next_item()
            return

        # pylint: disable=superfluous-parens
        if self.settings["rounding_value"] and (r := (score % self.settings["rounding_value"])):
            self.info_log("rounding bonus score %s remainder of %s", score, r)
            if self.settings["rounding_direction"] == "down":
                score -= r
            else:
                score += self.settings["rounding_value"] - r

        self.info_log("Bonus Entry '%s': score: %s player_score_entry: %s=%s",
                      entry['entry'], score, entry['player_score_entry'], hits)

        self.bonus_score += score
        self.machine.events.post("bonus_entry", entry=entry['entry'],
                                 score=score, text=entry['text'],
                                 bonus_score=self.bonus_score, hits=hits)
        if entry.get("event"):
            self.machine.events.post(entry['event'], score=score,
                                     bonus_score=self.bonus_score, hits=hits)
        if entry['reset_player_score_entry']:
            self.player.vars[entry['player_score_entry']] = 0

        self.delay.add(name='bonus', ms=self.display_delay,
                       callback=self._bonus_next_item)

    def _subtotal(self):
        if self.player.vars.get("bonus_multiplier", 1) == 1:
            self.debug_log(
                "Skipping bonus_multiplier event because the multiplier is 1.")
            self._total_bonus()

        else:
            self.debug_log("Bonus subtotal: %s", self.bonus_score)
            self.machine.events.post('bonus_entry', entry='subtotal',
                                     text="Subtotal", score=self.bonus_score)
            '''event: bonus_subtotal

            desc: Posted by the bonus mode after all the individual bonus
            entries have been posted and processed.

            This event is typically posted just before the bonus multiplier
            screen, so if the bonus multiplier is 1, then this event will
            be skipped.

            args:

            score: The score of the bonus (so far)

            '''
            self.delay.add(name='bonus', ms=self.display_delay,
                           callback=self._do_multiplier)

    def _do_multiplier(self):
        multiplier = self.player.vars.get("bonus_multiplier", 1)
        self.debug_log("Bonus multiplier: %s", multiplier)
        self.machine.events.post('bonus_entry', entry='multiplier',
                                 text="Multiplier", score=multiplier)
        '''event: bonus_multiplier

        desc: Posted after bonus subtotal and used to trigger the bonus
        multiplier screen. If the bonus multiplier is 1, then this event is
        skipped.

        args:

        score: The numeric value of the bonus multiplier.

        '''
        self.bonus_score *= multiplier
        self.delay.add(name='bonus', ms=self.display_delay,
                       callback=self._total_bonus)

    def _total_bonus(self):
        self.player.add_with_kwargs("score", self.bonus_score,
                                    source=self.name)
        self.debug_log("Bonus Total: %s", self.bonus_score)
        self.machine.events.post('bonus_entry', entry='total',
                                 text="Total Bonus", score=self.bonus_score)

        if not self.settings['end_bonus_event']:
            self.delay.add(name='bonus', ms=self.display_delay,
                           callback=self._end_bonus)

    def _end_bonus(self, **kwargs):
        del kwargs
        self.debug_log("Bonus done")
        keep_multiplier = self.settings['keep_multiplier']

        if not keep_multiplier.evaluate({}):
            self.player.bonus_multiplier = 1
        self.stop()
