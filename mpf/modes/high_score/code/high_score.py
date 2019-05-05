"""Contains the High Score mode code."""

import asyncio

from typing import Generator

from mpf.core.async_mode import AsyncMode
from mpf.core.player import Player


class HighScore(AsyncMode):

    """High score mode.

    Mode which runs during the game ending process to check for high scores and lets the players enter their names or
    initials.
    """

    __slots__ = ["data_manager", "high_scores", "high_score_config", "pending_award"]

    def __init__(self, machine, config, name, path):
        """Initialise high score mode."""
        self.data_manager = None
        self.high_scores = None
        self.high_score_config = None
        self.pending_award = None
        super().__init__(machine, config, name, path)

    def mode_init(self):
        """Initialise high score mode."""
        self.data_manager = self.machine.create_data_manager('high_scores')
        self.high_scores = self.data_manager.get_data()

        self.high_score_config = self.machine.config_validator.validate_config(
            config_spec='high_score',
            source=self.config.get('high_score', {}),
            section_name='high_score')

        # if data is invalid. do not use it
        if self.high_scores and not self._validate_data(self.high_scores):
            self.log.warning("High score data failed validation. Resetting to defaults.")
            self.high_scores = None

        # Load defaults if no high_scores are stored
        if not self.high_scores:
            self.high_scores = {k: [(next(iter(a.keys())), next(iter(a.values()))) for a in v] for (k, v) in
                                self.config['high_score']['defaults'].items()}

        self._create_machine_vars()
        self.pending_award = None

    def _validate_data(self, data):
        try:
            for category in data:
                if category not in self.high_score_config['categories']:
                    self.log.warning("Found invalid category in high scores.")
                    return False

                for entry in data[category]:
                    if not isinstance(entry, tuple) or len(entry) != 2:
                        self.log.warning("Found invalid high score entry.")
                        return False

                    if not isinstance(entry[0], str) or not isinstance(entry[1], (int, float)):
                        self.log.warning("Found invalid data type in high score entry.")
                        return False

        except TypeError:
            return False

        return True

    def _create_machine_vars(self):
        """Create all machine vars in the machine on start.

        This is used in attract mode.
        """
        for category, entries in self.high_score_config['categories'].items():
            try:
                for position, (label, (name, value)) in (
                        enumerate(zip(entries,
                                      self.high_scores[category]))):

                    self.machine.set_machine_var(
                        name=category + str(position + 1) + '_label',
                        value=label)

                    '''machine_var: (high_score_category)(position)_label

                    desc: The "label" of the high score for that specific
                    score category and position. For example,
                    ``score1_label`` holds the label for the #1 position
                    of the "score" player variable (which might be "GRAND
                    CHAMPION").

                    '''

                    self.machine.set_machine_var(
                        name=category + str(position + 1) + '_name',
                        value=name)

                    '''machine_var: (high_score_category)(position)_name

                    desc: Holds the player's name (or initials) for the
                    high score for that category and position.

                    '''

                    self.machine.set_machine_var(
                        name=category + str(position + 1) + '_value',
                        value=value)

                    '''machine_var: (high_score_category)(position)_value

                    desc: Holds the numeric value for the high score
                    for that category and position.

                    '''

            except KeyError:
                self.high_scores[category] = list()

    # pylint: disable-msg=too-many-nested-blocks
    @asyncio.coroutine
    def _run(self) -> Generator[int, None, None]:
        """Run high score mode."""
        if not self.machine.game or not self.machine.game.player_list:
            self.log.warning("High Score started but there was no game. Will not start.")
            return

        new_high_score_list = {}

        # iterate highscore categories
        for category_name, award_names in self.high_score_config['categories'].items():
            new_list = list()

            # add the existing high scores to the list

            # make sure we have this category in the existing high scores
            if category_name in self.high_scores:
                for category_high_scores in self.high_scores[category_name]:
                    new_list.append(category_high_scores)

            # add the players scores from this game to the list
            for player in self.machine.game.player_list:
                # if the player var is 0, don't add it. This prevents
                # values of 0 being added to blank high score lists
                if player[category_name]:
                    new_list.append((player, player[category_name]))

            # sort if from highest to lowest
            new_list.sort(key=lambda x: x[1], reverse=(not category_name in self.high_score_config['reverse_sort']))

            # scan through and see if any of our players are in this list
            i = 0
            while i < len(award_names) and i < len(new_list):
                entry = new_list[i]
                if isinstance(entry[0], Player):
                    player, value = entry
                    # ask player for initials if we do not know them
                    if not player.initials:
                        try:
                            player.initials = yield from self._ask_player_for_initials(player, award_names[i],
                                                                                       value)
                        except asyncio.TimeoutError:
                            del new_list[i]
                            # no entry when the player missed the timeout
                            continue
                    # add high score
                    new_list[i] = (player.initials, value)
                    # show award slide
                    yield from self._show_award_slide(player.initials, award_names[i], value)

                # next entry
                i += 1

            # save the new list for this category and trim it so that it's the length specified in the config
            new_high_score_list[category_name] = new_list[:len(award_names)]

        self.high_scores = new_high_score_list
        self._write_scores_to_disk()
        self._create_machine_vars()

    @asyncio.coroutine
    # pylint: disable-msg=too-many-arguments
    def _ask_player_for_initials(self, player: Player, award_label: str, value: int) -> Generator[int, None, str]:
        """Show text widget to ask player for initials."""
        self.info_log("New high score. Player: %s, award_label: %s"
                      ", Value: %s", player, award_label, value)

        self.machine.events.post('high_score_enter_initials',
                                 award=award_label,
                                 player_num=player.number,
                                 value=value)

        event_result = yield from asyncio.wait_for(
            self.machine.events.wait_for_event("text_input_high_score_complete"),
            timeout=self.high_score_config['enter_initials_timeout'],
            loop=self.machine.clock.loop
        )   # type: dict

        return event_result["text"] if "text" in event_result else ''

    @asyncio.coroutine
    def _show_award_slide(self, player_name: str, award: str, value: int) -> Generator[int, None, None]:
        if not self.high_score_config['award_slide_display_time']:
            return

        self.machine.events.post(
            'high_score_award_display',
            player_name=player_name,
            award=award,
            value=value)
        self.machine.events.post(
            '{}_award_display'.format(award),
            player_name=player_name,
            award=award,
            value=value)
        yield from asyncio.sleep(self.high_score_config['award_slide_display_time'] / 1000,
                                 loop=self.machine.clock.loop)

    def _write_scores_to_disk(self) -> None:
        self.data_manager.save_all(data=self.high_scores)
