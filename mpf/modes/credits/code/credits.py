"""Contains the Credit (coin play) mode code"""

# credits.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf
from math import floor

from mpf.system.mode import Mode


class Credits(Mode):

    def mode_init(self):

        self.auto_stop_on_ball_end = False

        self.credit_units_per_game = 0
        self.credit_units_inserted = 0
        self.credit_unit = 0
        self.max_credit_units = 0
        self.pricing_tiers = set()

        self.credits_config = self.machine.config['credits']

        if 'credits' in self.config:
            self.credits_config.update(self.config['credits'])

        self.credits_config = self.machine.config_processor.process_config2(
            'credits', self.credits_config, 'credits')

    def mode_start(self, **kwargs):
        if self.credits_config['free_play']:
            self.stop()
        else:
            self._calculate_credit_units()
            self._calculate_pricing_tiers()
            self.enable_coin_play()

    def _calculate_credit_units(self):
        # "credit units" are how we handle fractional credits (since most
        # pinball machines show credits as fractions instead of decimals).
        # We convert everything to the smallest coin unit and then track
        # how many of those a game takes. So price of $0.75 per game with a
        # quarter slot means a credit unit is 0.25 and the game needs 3 credit
        # units to start. This is all hidden from the player

        # We need to calculate it differently depending on how the coin switch
        # values relate to game cost.

        min_currency_value = min(x['value'] for x in
                                 self.credits_config['switches'])
        price_per_game = self.credits_config['pricing_tiers'][0]['price']

        if min_currency_value == price_per_game:
            self.credit_unit = min_currency_value

        elif min_currency_value < price_per_game:
            self.credit_unit = price_per_game - min_currency_value
            if self.credit_unit > min_currency_value:
                self.credit_unit = min_currency_value

        elif min_currency_value > price_per_game:
            self.credit_unit = min_currency_value - price_per_game
            if self.credit_unit > price_per_game:
                self.credit_unit = price_per_game

        self.log.debug("Calculated the credit unit to be %s based on a minimum"
                       "currency value of %s and a price per game of %s",
                       self.credit_unit, min_currency_value, price_per_game)

        self.credit_units_per_game = (
            int(self.credits_config['pricing_tiers'][0]['price'] /
                self.credit_unit))

        self.log.debug("Credit units per game: %s", self.credit_units_per_game)

        if self.credits_config['max_credits']:
            self.max_credit_units = (self.credit_units_per_game *
                                     self.credits_config['max_credits'])

    def _calculate_pricing_tiers(self):
        # pricing tiers are calculated with a set of tuples which indicate the
        # credit units for the price break as well as the "bump" in credit
        # units that should be added once that break is passed.

        for pricing_tier in self.credits_config['pricing_tiers']:
            credit_units = pricing_tier['price'] / self.credit_unit
            actual_credit_units = self.credit_units_per_game * pricing_tier['credits']
            bonus = actual_credit_units - credit_units

            self.log.debug("Pricing Tier Bonus. Price: %s, Credits: %s. "
                           "Credit units for this tier: %s, Credit units this "
                           "tier buys: %s, Bonus bump needed: %s",
                           pricing_tier['price'], pricing_tier['credits'],
                           credit_units, actual_credit_units, bonus)

            self.pricing_tiers.add((credit_units, bonus))

    def enable_coin_play(self):
        if self.credits_config['persist_credits_while_off_time']:
            self.machine.create_machine_var(name='credit_units', value=0,
                persist=True,
                expire_secs=self.credits_config[
                    'persist_credits_while_off_time'])
        else:
            self.machine.create_machine_var(name='credit_units', value=0)

        self.machine.create_machine_var('credits_string', ' ')
        self.machine.create_machine_var('credits_value', '0')
        self.machine.create_machine_var('credits_whole_num', 0)
        self.machine.create_machine_var('credits_numerator', 0)
        self.machine.create_machine_var('credits_denominator', 0)
        self._update_credit_strings()

        self._enable_credit_switch_handlers()

        # setup switch handlers

        self.machine.events.add_handler('player_add_request',
                                        self._player_add_request)
        self.machine.events.add_handler('player_add_success',
                                        self._player_add_success)

    def _player_add_request(self):

        # if credits >= 1, return true, else false

        pass

    def _player_add_success(self, **kwargs):
        pass

        # subtract 1 credit from list

    def _enable_credit_switch_handlers(self):
        for switch_settings in self.credits_config['switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch_settings['switch'].name,
                callback=self._credit_switch_callback,
                callback_kwargs={'value': switch_settings['value'],
                                 'type_': switch_settings['type']})

        for switch in self.credits_config['service_credits_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self._service_credit_callback)

    def _credit_switch_callback(self, value, type_):

        # todo add to earnings report

        # figure out credit units
        new_credit_units = value / self.credit_unit

        current_credit_units = self.machine.get_machine_var('credit_units')

        total_credit_units = new_credit_units + current_credit_units

        # check for pricing tier
        bonus_credit_units = 0
        for credit_units, bonus in self.pricing_tiers:
            if total_credit_units % credit_units == 0:
                bonus_credit_units += bonus

        total_credit_units += bonus_credit_units

        self.machine.set_machine_var('credit_units', total_credit_units)

        # todo check max

        self._update_credit_strings()

    def _service_credit_callback(self):
        # todo audit
        self.machine.set_machine_var('credit_units',
            self.machine.get_machine_var('credit_units') +
            self.credit_units_per_game)

        self._update_credit_strings()
        # todo check max

    def _add_credit_units(self, credit_units):



        pass


    def _update_credit_strings(self):
        machine_credit_units = self.machine.get_machine_var('credit_units')
        whole_num = int(floor(machine_credit_units /
                              self.credit_units_per_game))
        numerator = int(machine_credit_units % self.credit_units_per_game)
        denominator = int(self.credit_units_per_game)

        if numerator:
            if whole_num:
                display_fraction = '{} {}/{}'.format(whole_num, numerator, denominator)
            else:
                display_fraction = '{}/{}'.format(numerator, denominator)

        else:
            display_fraction = str(whole_num)

        if self.credits_config['free_play']:
            display_string = self.credits_config['free_play_string']
        else:
            display_string = '{} {}'.format(
                self.credits_config['credits_string'], display_fraction)
        self.machine.set_machine_var('credits_string', display_string)
        self.machine.set_machine_var('credits_value', display_fraction)
        self.machine.set_machine_var('credits_whole_num', whole_num)
        self.machine.set_machine_var('credits_numerator', numerator)
        self.machine.set_machine_var('credits_denominator', denominator)

    def audit(self):
        pass







# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.