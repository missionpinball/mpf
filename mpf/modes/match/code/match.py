"""Contains the Match mode code."""
import random

import math

from mpf.core.settings_controller import SettingEntry

from mpf.core.async_mode import AsyncMode


class Match(AsyncMode):

    """Match mode."""

    __slots__ = []

    def __init__(self, *args, **kwargs):
        """Initialise match mode."""
        super().__init__(*args, **kwargs)
        # add setting
        self.machine.settings.add_setting(SettingEntry("match_percentage", "Match percentage", 500,
                                                       "match_percentage", 10,
                                                       {0: "off", 2: "2%", 5: "5%", 10: "10%", 15: "15%", 30: "30%",
                                                        50: "50%"}, "standard"))

    def _get_match_numbers(self):
        """Calculate match numbers."""
        match_numbers = []
        for player in self.machine.game.player_list:
            match_numbers.append(player.score % 100)
        return match_numbers

    def _get_winner_number(self, match_numbers, match_percentage) -> int:
        """Find the winning number.

        Return the winning number.
        """
        # check if a player will win
        if random.randint(0, 100) < math.pow(match_percentage, len(set(match_numbers))):
            # we got a winner
            return random.choice(match_numbers)

        step = self.config.get("mode_settings", {}).get("non_match_number_step", 1)

        # no winner. return some other number
        non_winning_numbers = list(set(range(0, 100, step)) - set(match_numbers))
        return random.choice(non_winning_numbers)

    async def _run(self) -> None:
        """Run match mode."""
        # no player, no match
        if not self.machine.game or not self.machine.game.player_list:
            return

        match_percentage = self.machine.settings.get_setting_value("match_percentage")

        match_numbers = self._get_match_numbers()
        winner_number = self._get_winner_number(match_numbers, match_percentage)
        winners = match_numbers.count(winner_number)

        event_args = {
            "winner_number": winner_number,
            "winners": winners
        }

        for i in range(0, self.machine.game.max_players):
            event_args["match_number{}".format(i)] = match_numbers[i] if len(match_numbers) > i else ""

        if not winners:
            # no winner
            await self.machine.events.post_queue_async("match_no_match", **event_args)
            '''event: match_no_match

            desc: All players missed the match number.

            args:
              winner_number: Winner number
              winners: Number of winners (always 0 here)
              match_number0: Match number for player 0
              match_number1: Match number for player 1
              match_numberX: Match number for player X (up to max players)
            '''
        else:
            # we got a winner
            await self.machine.events.post_queue_async("match_has_match", **event_args)
            '''event: match_has_match

            desc: At least one player has a match.

            args:
              winner_number: Winner number
              winners: Number of winners (always more than 0 here)
              match_number0: Match number for player 0
              match_number1: Match number for player 1
              match_numberX: Match number for player X (up to max players)
            '''
        # that is it. credits mode should hook into the match_has_match event and award credits
