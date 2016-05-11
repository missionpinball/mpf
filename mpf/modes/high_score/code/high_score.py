"""Contains the High Score mode code"""

from collections import OrderedDict
from mpf.core.data_manager import DataManager
from mpf.core.mode import Mode
from mpf.core.player import Player


class HighScore(Mode):

    def mode_init(self):
        self.data_manager = DataManager(self.machine, 'high_scores')
        self.high_scores = self.data_manager.get_data()

        self.high_score_config = self.machine.config_validator.validate_config(
            config_spec='high_score',
            source=self._get_merged_settings('high_score'),
            section_name='high_score')

        self.player_name_handler = None

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

        self.add_mode_event_handler('text_input_high_score_complete',
                                    self._receive_player_name)

        if self._check_for_high_scores():
            self._start_sending_switches()
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

        self.high_scores_done()

    # pylint: disable-msg=too-many-arguments
    def _get_player_name(self, player, config_cat_name, index, award_label, value):
        if not self.pending_award:

            self.log.info("New high score. Player: %s, award_label: %s"
                          ", Value: %s", player, award_label, value)

            self.pending_award = (config_cat_name, index, value, award_label)

            self.machine.create_machine_var(name='new_high_score_award',
                                            value=award_label)
            self.machine.create_machine_var(name='new_high_score_player_num',
                                            value=player.number)
            self.machine.create_machine_var(name='new_high_score_value',
                                            value=value)

            self.machine.bcp.send(bcp_command='trigger',
                                  name='new_high_score',
                                  award=award_label,
                                  player_num=player.number,
                                  value=value)

    def _receive_player_name(self, text, mode):
        del mode

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
        self.send_award_slide_event(
            award_slide_name='high_score_award_display',
            player_name=player_name,
            award=award,
            value=value)
        self.send_award_slide_event(
            award_slide_name='{}_award_display'.format(award),
            player_name=player_name,
            award=award,
            value=value)
        self.delay.add(
            name='award_timer',
            ms=self.high_score_config['award_slide_display_time'],
            callback=self._get_player_names)

    def high_scores_done(self):
        self._stop_sending_switches()
        self.high_scores = self.new_high_score_list
        self._write_scores_to_disk()
        self.player_name_handler = None
        self.stop()

    def _write_scores_to_disk(self):
        self.data_manager.save_all(data=self.high_scores)
        self._create_machine_vars()

    def _start_sending_switches(self):
        for switch in self.machine.switches.items_tagged(
                self.high_score_config['shift_left_tag']):
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self.send_left)

        for switch in self.machine.switches.items_tagged(
                self.high_score_config['shift_right_tag']):
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self.send_right)

        for switch in self.machine.switches.items_tagged(
                self.high_score_config['select_tag']):
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self.send_select)

    def _stop_sending_switches(self):
        for switch in self.machine.switches.items_tagged(
                self.high_score_config['shift_left_tag']):
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self.send_left)
        for switch in self.machine.switches.items_tagged(
                self.high_score_config['shift_right_tag']):
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self.send_right)

        for switch in self.machine.switches.items_tagged(
                self.high_score_config['select_tag']):
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self.send_select)

    def send_left(self):
        self.machine.bcp.send(bcp_command='trigger',
                              name='switch_{}_active'.format(
                                  self.high_score_config['shift_left_tag']))

    def send_right(self):
        self.machine.bcp.send(bcp_command='trigger',
                              name='switch_{}_active'.format(
                                  self.high_score_config['shift_right_tag']))

    def send_select(self):
        self.machine.bcp.send(bcp_command='trigger',
                              name='switch_{}_active'.format(
                                  self.high_score_config['select_tag']))

    def send_award_slide_event(self, award_slide_name, player_name, award,
                               value):
        self.machine.bcp.send(bcp_command='trigger',
                              name=award_slide_name,
                              player_name=player_name,
                              award=award,
                              value=value)
