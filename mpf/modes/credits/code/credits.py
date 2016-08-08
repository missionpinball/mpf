"""Contains the Credit (coin play) mode code."""

from math import floor

from mpf.core.mode import Mode


class Credits(Mode):

    """Mode which manages the credits and prevents the game from starting without credits."""

    def __init__(self, machine, config, name, path):
        """Initialise credits mode."""
        self.data_manager = None
        self.earnings = None

        self.credit_units_per_game = None
        self.credit_unit = None
        self.pricing_tiers = None
        self.credit_units_for_pricing_tiers = None
        self.reset_pricing_tier_count_this_game = None
        self.credits_config = None
        super().__init__(machine, config, name, path)

    def mode_init(self):
        """Initialise mode."""
        self.data_manager = self.machine.create_data_manager('earnings')
        self.earnings = self.data_manager.get_data()

        self.credit_units_per_game = 0
        self.credit_unit = 0
        self.pricing_tiers = set()
        self.credit_units_for_pricing_tiers = 0
        self.reset_pricing_tier_count_this_game = False

        self.credits_config = self.machine.config_validator.validate_config(
            config_spec='credits',
            source=self._get_merged_settings('credits'),
            section_name='credits')

    def mode_start(self, **kwargs):
        """Start mode."""
        self.add_mode_event_handler('enable_free_play',
                                    self.enable_free_play)
        self.add_mode_event_handler('enable_credit_play',
                                    self.enable_credit_play)
        self.add_mode_event_handler('toggle_credit_play',
                                    self.toggle_credit_play)
        self.add_mode_event_handler('slam_tilt',
                                    self.clear_all_credits)

        if self.credits_config['free_play']:
            self.enable_free_play(post_event=False)
        else:
            self._calculate_credit_units()
            self._calculate_pricing_tiers()
            self.enable_credit_play(post_event=False)

    def mode_stop(self, **kwargs):
        """Stop mode."""
        self.enable_free_play()

    def _calculate_credit_units(self):
        # "credit units" are how we handle fractional credits (since most
        # pinball machines show credits as fractions instead of decimals).
        # We convert everything to the smallest coin unit and then track
        # how many of those a game takes. So price of $0.75 per game with a
        # quarter slot means a credit unit is 0.25 and the game needs 3 credit
        # units to start. This is all hidden from the player

        # We need to calculate it differently depending on how the coin switch
        # values relate to game cost.

        if self.credits_config['switches']:
            min_currency_value = min(x['value'] for x in
                                     self.credits_config['switches'])
        else:
            min_currency_value = (
                self.credits_config['pricing_tiers'][0]['price'])

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

    def enable_credit_play(self, post_event=True, **kwargs):
        """Enable credits play."""
        del kwargs

        self.credits_config['free_play'] = False

        credit_units = self._get_credit_units()

        if self.credits_config['persist_credits_while_off_time']:
            self.machine.create_machine_var(name='credit_units',
                                            value=credit_units,
                                            persist=True,
                                            expire_secs=self.credits_config[
                                                'persist_credits_while_off_time'])
        else:
            self.machine.create_machine_var(name='credit_units',
                                            value=credit_units)

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
        self.machine.events.add_handler('request_to_start_game',
                                        self._request_to_start_game)
        self.machine.events.add_handler('player_add_success',
                                        self._player_add_success)
        self.machine.events.add_handler('mode_game_started',
                                        self._game_started)
        self.machine.events.add_handler('mode_game_stopped',
                                        self._game_ended)
        self.machine.events.add_handler('ball_starting',
                                        self._ball_starting)
        if post_event:
            self.machine.events.post('enabling_credit_play')
        '''event: enabling_credit_play
        desc: The game is no longer on free play. Credits are required to
        start a game. This event is also posted on MPF boot if the credits mode
         is enabled and the game is not set to free play.
        '''

    def enable_free_play(self, post_event=True, **kwargs):
        """Enable free play."""
        del kwargs
        self.credits_config['free_play'] = True

        self.machine.events.remove_handler(self._player_add_request)
        self.machine.events.remove_handler(self._request_to_start_game)
        self.machine.events.remove_handler(self._player_add_success)
        self.machine.events.remove_handler(self._game_ended)
        self.machine.events.remove_handler(self._game_started)
        self.machine.events.remove_handler(self._ball_starting)

        self._disable_credit_switch_handlers()

        self._update_credit_strings()

        if post_event:
            self.machine.events.post('enabling_free_play')
        '''event: enabling_free_play
        desc: Credits are no longer required to start a game. This event is
        also posted on MPF boot if the credits mode is enabled and the game is
        set to free play.
        '''

    def toggle_credit_play(self, **kwargs):
        """Toggle between free and credits play."""
        del kwargs

        if self.credits_config['free_play']:
            self.enable_credit_play()
        else:
            self.enable_free_play()

    def _get_credit_units(self):
        credit_units = self.machine.get_machine_var('credit_units')
        if not credit_units:
            credit_units = 0
        return credit_units

    def _player_add_request(self):
        if (self._get_credit_units() >=
                self.credit_units_per_game):
            self.log.debug("Received request to add player. Request Approved")
            return True

        else:
            self.log.debug("Received request to add player. Request Denied")
            self.machine.events.post("not_enough_credits")
            '''event: not_enough_credits
            desc: A player has pushed the start button, but the game is not set
            to free play and there are not enough credits to start a game or
            add a player.
            '''
            return False

    def _request_to_start_game(self):
        if (self._get_credit_units() >=
                self.credit_units_per_game):
            self.log.debug("Received request to start game. Request Approved")
            return True

        else:
            self.log.debug("Received request to start game. Request Denied")
            self.machine.events.post("not_enough_credits")
            # event docstring covered in _player_add_request() method
            return False

    def _player_add_success(self, **kwargs):
        del kwargs
        new_credit_units = (self._get_credit_units() -
                            self.credit_units_per_game)

        if new_credit_units < 0:
            self.log.warning("Somehow credit units went below 0?!? Resetting "
                             "to 0.")
            new_credit_units = 0

        self.machine.set_machine_var('credit_units', new_credit_units)
        self._update_credit_strings()

    def _enable_credit_switch_handlers(self):
        for switch_settings in self.credits_config['switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch_settings['switch'].name,
                callback=self._credit_switch_callback,
                callback_kwargs={'value': switch_settings['value'],
                                 'audit_class': switch_settings['type']})

        for switch in self.credits_config['service_credits_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name,
                callback=self._service_credit_callback)

    def _disable_credit_switch_handlers(self):
        for switch_settings in self.credits_config['switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch_settings['switch'].name,
                callback=self._credit_switch_callback)

        for switch in self.credits_config['service_credits_switch']:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self._service_credit_callback)

    def _credit_switch_callback(self, value, audit_class):
        self._add_credit_units(credit_units=value / self.credit_unit)
        self._audit(value, audit_class)
        self._reset_timeouts()

    def _service_credit_callback(self):
        self.log.debug("Service Credit Added")
        self.add_credit(price_tiering=False)
        self._audit(1, 'service_credit')

    def _add_credit_units(self, credit_units, price_tiering=True):
        self.log.debug("Adding %s credit_units. Price tiering: %s",
                       credit_units, price_tiering)

        previous_credit_units = self._get_credit_units()
        total_credit_units = credit_units + previous_credit_units

        # check for pricing tier
        if price_tiering:
            self.credit_units_for_pricing_tiers += credit_units
            bonus_credit_units = 0
            for tier_credit_units, bonus in self.pricing_tiers:
                if self.credit_units_for_pricing_tiers % tier_credit_units == 0:
                    bonus_credit_units += bonus

            total_credit_units += bonus_credit_units

        max_credit_units = (self.credits_config['max_credits'] *
                            self.credit_units_per_game)

        if max_credit_units and total_credit_units > max_credit_units:
            self.log.debug("Max credits reached")
            self._update_credit_strings()
            self.machine.events.post('max_credits_reached')
            '''event: max_credits_reached
            desc: Credits have just been added to the machine, but the
            configured maximum number of credits has been reached.'''
            self.machine.set_machine_var('credit_units', max_credit_units)

        if max_credit_units > previous_credit_units:
            self.log.debug("Credit units added")
            self.machine.set_machine_var('credit_units', total_credit_units)
            self._update_credit_strings()
            self.machine.events.post('credits_added')
            '''event: credits_added
            desc: Credits (or partial credits) have just been added to the
            machine.'''

    def add_credit(self, price_tiering=True):
        """Add a single credit to the machine.

        Args:
            price_tiering: Boolean which controls whether this credit will be
                eligible for the pricing tier bonuses. Default is True.

        """
        self._add_credit_units(self.credit_units_per_game, price_tiering)

    def _reset_pricing_tier_credits(self):
        if not self.reset_pricing_tier_count_this_game:
            self.log.debug("Resetting pricing tier credit count")
            self.credit_units_for_pricing_tiers = 0
            self.reset_pricing_tier_count_this_game = True

    def _ball_starting(self, **kwargs):
        del kwargs
        if self.player.number == 1 and self.player.ball == 2:
            self._reset_pricing_tier_credits()

    def _update_credit_strings(self):
        machine_credit_units = self._get_credit_units()
        if self.credit_units_per_game > 0:
            whole_num = int(floor(machine_credit_units /
                            self.credit_units_per_game))
            numerator = int(machine_credit_units % self.credit_units_per_game)
            denominator = int(self.credit_units_per_game)
        else:
            whole_num = 0
            numerator = 0
            denominator = 0

        if numerator:
            if whole_num:
                display_fraction = '{} {}/{}'.format(whole_num, numerator,
                                                     denominator)
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

    def _audit(self, value, audit_class):
        if audit_class not in self.earnings:
            self.earnings[audit_class] = dict()
            self.earnings[audit_class]['total_value'] = 0
            self.earnings[audit_class]['count'] = 0

        self.earnings[audit_class]['total_value'] += value
        self.earnings[audit_class]['count'] += 1

        self.data_manager.save_all(data=self.earnings)

    def _game_started(self):
        self.log.debug("Removing credit clearing delays")
        self.delay.remove('clear_fractional_credits')
        self.delay.remove('clear_all_credits')

    def _reset_timeouts(self):
        if self.credits_config['fractional_credit_expiration_time']:
            self.log.debug("Adding delay to clear fractional credits")
            self.delay.reset(
                ms=self.credits_config['fractional_credit_expiration_time'],
                callback=self._clear_fractional_credits,
                name='clear_fractional_credits')

        if self.credits_config['credit_expiration_time']:
            self.log.debug("Adding delay to clear credits")
            self.delay.reset(
                ms=self.credits_config['credit_expiration_time'],
                callback=self.clear_all_credits,
                name='clear_all_credits')

    def _game_ended(self):
        self._reset_timeouts()

        self.reset_pricing_tier_count_this_game = False

    def _clear_fractional_credits(self):
        self.log.debug("Clearing fractional credits")

        credit_units = self._get_credit_units()
        credit_units -= credit_units % self.credit_units_per_game

        self.machine.set_machine_var('credit_units', credit_units)
        self._update_credit_strings()

    def clear_all_credits(self):
        """Clear all credits."""
        self.log.debug("Clearing all credits")
        self.machine.set_machine_var('credit_units', 0)
        self._update_credit_strings()
