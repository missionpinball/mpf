"""Contains the High Score mode code."""

import asyncio

from mpf.core.async_mode import AsyncMode
from mpf.core.player import Player


class HighScore(AsyncMode):

    """Mode which tracks high scores and lets the player enter its initials."""

    def __init__(self, machine, config, name, path):
        """Initialise high score mode."""
        self.data_manager = None
        self.high_scores = None
        self.high_score_config = None
        self.pending_award = None
        self.new_high_score_list = None
        super().__init__(machine, config, name, path)

    def mode_init(self):
        """Initialise high score mode."""
        self.data_manager = self.machine.create_data_manager('high_scores')
        self.high_scores = self.data_manager.get_data()

        self.high_score_config = self.machine.config_validator.validate_config(
            config_spec='high_score',
            source=self._get_merged_settings('high_score'),
            section_name='high_score')

        # Load defaults if no high_scores are stored
        if not self.high_scores:
            self.high_scores = {k: [(next(iter(a.keys())), next(iter(a.values()))) for a in v] for (k, v) in
                                self.config['high_score']['defaults'].items()}

        self._create_machine_vars()
        self.pending_award = None

    def _create_machine_vars(self):
        """Create all machine vars in the machine on start.

        This is used in attract mode.
        """
        for category in self.high_score_config['categories']:
            for entries in category:
                try:
                    for position, (label, (name, value)) in (
                            enumerate(zip(category[entries],
                                          self.high_scores[entries]))):

                        self.machine.create_machine_var(
                            name=entries + str(position + 1) + '_label',
                            value=label)

                        '''machine_var: (high_score_category)(position)_label

                        desc: The "label" of the high score for that specific
                        score category and position. For example,
                        ``score1_label`` holds the label for the #1 position
                        of the "score" player variable (which might be "GRAND
                        CHAMPION").

                        '''

                        self.machine.create_machine_var(
                            name=entries + str(position + 1) + '_name',
                            value=name)

                        '''machine_var: (high_score_category)(position)_name

                        desc: Holds the player's name (or initials) for the
                        high score for that category and position.

                        '''

                        self.machine.create_machine_var(
                            name=entries + str(position + 1) + '_value',
                            value=value)

                        '''machine_var: (high_score_category)(position)_value

                        desc: Holds the numeric value for the high score
                        for that category and position.

                        '''

                except KeyError:
                    self.high_scores[entries] = list()

    @asyncio.coroutine
    def _run(self):
        """Run high score mode."""
        if not self.machine.game.player_list:
            return

        self.new_high_score_list = {}

        # iterate highscore categories
        for category_settings in self.high_score_config['categories']:
            for category_name, award_names in category_settings.items():

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
                new_list.sort(key=lambda x: x[1], reverse=True)

                # trim it so that it's the length specified in the config
                new_list = new_list[:len(award_names)]

                # save the new list for this category
                self.new_high_score_list[category_name] = new_list

                # scan through and see if any of our players are in this list
                for i in range(0, len(new_list)):
                    entry = new_list[i]
                    if isinstance(entry[0], Player):
                        yield from self._ask_player_for_initials(entry[0], category_name, i, award_names[i], entry[1])

        self.high_scores = self.new_high_score_list
        self._write_scores_to_disk()

        return

    @asyncio.coroutine
    # pylint: disable-msg=too-many-arguments
    def _ask_player_for_initials(self, player, config_cat_name, index, award_label, value):

        self.info_log("New high score. Player: %s, award_label: %s"
                      ", Value: %s", player, award_label, value)

        self.machine.events.post('high_score_enter_initials',
                                 award=award_label,
                                 player_num=player.number,
                                 value=value)

        event_result = yield from self.machine.events.wait_for_event("text_input_high_score_complete")

        if "text" not in event_result:
            event_result["text"] = ''

        self.new_high_score_list[config_cat_name][index] = (event_result["text"], value)

        yield from self._show_award_slide(event_result["text"], award_label, value)

    @asyncio.coroutine
    def _show_award_slide(self, player_name, award, value):
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

    def _write_scores_to_disk(self):
        self.data_manager.save_all(data=self.high_scores)
        self._create_machine_vars()
