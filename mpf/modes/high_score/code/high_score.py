"""Contains the High Score mode code"""

from collections import OrderedDict
from mpf.core.data_manager import DataManager
from mpf.core.mode import Mode


class HighScore(Mode):

    def mode_init(self):
        self.data_manager = DataManager(self.machine, 'high_scores')
        self.high_scores = self.data_manager.get_data()

        self.high_score_config = self.machine.config_validator.process_config2(
            config_spec='high_score',
            source=self._get_merged_settings('high_score'),
            section_name='high_score')

        self.player_name_handler = None

        self._create_machine_vars()
        self.pending_request = False

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

                except KeyError as e:
                    self.high_scores[entries] = list()

    def mode_start(self, **kwargs):
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
                for category_high_scores in self.high_scores[category_name]:
                    new_list.append(category_high_scores)

                # add the players scores from this game to the list
                for player in self.machine.game.player_list:
                    new_list.append((player, player[category_name]))

                # sort if from highest to lowest
                new_list.sort(key=lambda x: x[1], reverse=True)

                # trim it so that it's the length specified in the config
                new_list = new_list[:len(award_names)]

                # scan through and see if any of our players are in this list
                self.new_high_score_list[category_name] = new_list

                if player in [x[0] for x in new_list]:
                    high_score_change = True

        return high_score_change

    def _get_player_names(self):
        if not self.player_name_handler:
            self.machine.events.add_handler('high_score_complete',
                                            self._receive_player_name)

        for category_name, top_scores in self.new_high_score_list.items():
            for index, (player, value) in enumerate(top_scores):
                if player in self.machine.game.player_list:

                    for category_dict in self.high_score_config['categories']:
                        for config_cat_name in list(category_dict.keys()):

                            if config_cat_name == category_name:
                                award_label = (
                                    category_dict[config_cat_name][index])

                    if not self.pending_request:
                        self._get_player_name(player, award_label, value)
                    return

        self.high_scores_done()

    def _get_player_name(self, player, award_label, value):

        if not self.pending_request:

            self.log.info("New high score. Player: %s, award_label: %s"
                       ", Value: %s", player, award_label, value)

            self.pending_request = True

            self.machine.bcp.send(bcp_command='trigger',
                                  name='high_score',
                                  award=award_label,
                                  player_num=player.number,
                                  value=value)

    def _receive_player_name(self, award, player_name=None, **kwargs):
        self.pending_request = False

        valid_update = False

        if not player_name:
            player_name = ''

        for category_scores in self.high_score_config['categories']:

            for category_name in list(category_scores.keys()):
                for index, local_award in (
                        enumerate(category_scores[category_name])):
                    if local_award == award:

                        if (self.new_high_score_list[category_name][index][0]
                                in self.machine.game.player_list):
                            valid_update = True
                            value = (self.new_high_score_list[category_name]
                                                            [index][1])
                            self.new_high_score_list[category_name][index] = (
                                (player_name, value))

        # valid update is because if the MC sends multiple complete events for
        # the same award then this will send multiple requests for the next one
        # This is kind of a hack.. we'll revisit some day.
        if valid_update:

            if self.high_score_config['award_slide_display_time']:
                self.send_award_slide_event(
                    award_slide_name='high_score_award_display',
                    player_name=player_name,
                    award=award,
                    value=value)
                self.send_award_slide_event(
                    award_slide_name=award + '_award_display',
                    player_name=player_name,
                    award=award,
                    value=value)

                self.delay.add(name='award_timer',
                    ms=self.high_score_config['award_slide_display_time'],
                    callback=self._get_player_names)

            else:
                self._get_player_names()

    def high_scores_done(self):
        self._stop_sending_switches()
        self.high_scores = self.new_high_score_list
        self._write_scores_to_disk()
        self.machine.events.remove_handler(self._receive_player_name)
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
