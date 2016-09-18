"""Contains the High Score mode code."""

from collections import OrderedDict
from mpf.core.mode import Mode
from mpf.core.player import Player


class HighScore(Mode):

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

        self._create_machine_vars()
        self.pending_award = None

    def _create_machine_vars(self):
        for category in self.high_score_config['categories']:
            for entries in category:
                try:
                    for position, (label, (name, value)) in (
                            enumerate(zip(category[entries],
                                          self.high_scores[entries]))):

                        self.machine.create_machine_var(
                            name=entries + str(position + 1) + '_label',
                            value=label)
                        self.machine.create_machine_var(
                            name=entries + str(position + 1) + '_name',
                            value=name)
                        self.machine.create_machine_var(
                            name=entries + str(position + 1) + '_value',
                            value=value)

                except KeyError:
                    self.high_scores[entries] = list()

    def mode_start(self, **kwargs):
        """Start high score mode."""
        self.add_mode_event_handler('text_input_high_score_complete',
                                    self._receive_player_name)

        if self._check_for_high_scores():
            self.log.info("Player reached new high score")
            self._get_player_names()
        else:
            self.stop()

    def _check_for_high_scores(self):
        if not self.machine.game.player_list:
            return False

        high_score_change = False

        self.new_high_score_list = OrderedDict()

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
                for entry in new_list:
                    if isinstance(entry[0], Player):
                        high_score_change = True

        return high_score_change

    def _get_player_names(self):
        for category_name, top_scores in self.new_high_score_list.items():
            for index, (player, value) in enumerate(top_scores):
                if player in self.machine.game.player_list:

                    for category_dict in self.high_score_config['categories']:
                        if category_name not in category_dict:
                            continue
                        award_label = (
                            category_dict[category_name][index])

                        if not self.pending_award:
                            self._get_player_name(player,
                                                  category_name,
                                                  index, award_label,
                                                  value)
                        return

        self._high_scores_done()

    # pylint: disable-msg=too-many-arguments
    def _get_player_name(self, player, config_cat_name, index, award_label, value):
        if not self.pending_award:

            self.log.debug("New high score. Player: %s, award_label: %s"
                           ", Value: %s", player, award_label, value)

            self.pending_award = (config_cat_name, index, value, award_label)

            self.machine.events.post('high_score_enter_initials',
                                     award=award_label,
                                     player_num=player.number,
                                     value=value)

    def _receive_player_name(self, text, **kwargs):
        del kwargs

        if not text:
            text = ''

        if not self.pending_award:
            self._get_player_names()
            return

        config_cat_name, index, value, award_label = self.pending_award

        self.new_high_score_list[config_cat_name][index] = (text, value)

        self.pending_award = None

        if self.high_score_config['award_slide_display_time']:
            self._send_award_slide(text, award_label, value)

        else:
            self._get_player_names()

    def _send_award_slide(self, player_name, award, value):
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
        self.delay.add(
            name='award_timer',
            ms=self.high_score_config['award_slide_display_time'],
            callback=self._get_player_names)

    def _high_scores_done(self):
        self.high_scores = self.new_high_score_list
        self._write_scores_to_disk()
        self.stop()

    def _write_scores_to_disk(self):
        self.data_manager.save_all(data=self.high_scores)
        self._create_machine_vars()
