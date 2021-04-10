"""Contains the Credit (coin play) mode code."""

from math import floor

from mpf.core.placeholder_manager import NativeTypeTemplate
from mpf.core.settings_controller import SettingEntry

from mpf.core.mode import Mode


class Credits(Mode):

    """Mode which manages the credits and prevents the game from starting without credits."""

    __slots__ = ["data_manager", "earnings", "credit_units_per_game", "credit_unit", "pricing_tiers",
                 "credit_units_for_pricing_tiers", "reset_pricing_tier_count_this_game", "credits_config"]

    def __init__(self, *args, **kwargs):
        """Initialise credits mode."""
        self.data_manager = None
        self.earnings = None

        self.credit_units_per_game = None
        self.credit_unit = None
        self.pricing_tiers = None
        self.credit_units_for_pricing_tiers = None
        self.reset_pricing_tier_count_this_game = None
        self.credits_config = None
        super().__init__(*args, **kwargs)

    def mode_init(self):
        """Initialise mode."""
        self.data_manager = self.machine.create_data_manager('earnings')
        self.earnings = self.data_manager.get_data()

        # prevent crashes because of data corruption
        if not isinstance(self.earnings, dict):
            self.earnings = {}

        self.credit_units_per_game = 0
        self.credit_unit = 0
        self.pricing_tiers = set()
        self.credit_units_for_pricing_tiers = 0
        self.reset_pricing_tier_count_this_game = False

        self.credits_config = self.machine.config_validator.validate_config(
            config_spec='credits',
            source=self.machine.config.get('credits', {}),
            section_name='credits')

        for event in self.credits_config['reset_earnings_events']:
            self.machine.events.add_handler(event, self._reset_earnings)

        for event in self.credits_config['reset_credits_events']:
            self.machine.events.add_handler(event, self._reset_credits)

        # add setting
        self.machine.settings.add_setting(SettingEntry("free_play", "Free Play", 500,
                                                       "free_play", self.credits_config['free_play'],
                                                       {True: "Free Play", False: "Credit Play"}, "coin"))

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

        if self.machine.settings.get_setting_value("free_play"):
            self.enable_free_play(post_event=False)
        else:
            self._calculate_credit_units()
            self._calculate_pricing_tiers()
            self.enable_credit_play(post_event=False)

    def _reset_earnings(self, **kwargs):
        """Reset earnings."""
        del kwargs
        self.log.info("Resetting all earnings.")
        self.earnings = {}
        self.data_manager.save_all(data=self.earnings)

    def _reset_credits(self, **kwargs):
        """Reset credits."""
        del kwargs
        self.log.info("Resetting all credits.")
        self.clear_all_credits()

    def mode_stop(self, **kwargs):
        """Stop mode."""
        self._set_free_play_string()
        self._disable_credit_handlers()

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
            min_currency_value = min(x['value'].evaluate([]) for x in
                                     self.credits_config['switches'])
        else:
            try:
                min_currency_value = (
                    self.credits_config['pricing_tiers'][0]['price'].evaluate([]))
            except IndexError:
                min_currency_value = 1

        try:
            price_per_game = self.credits_config['pricing_tiers'][0]['price'].evaluate([])
            if self.credits_config['pricing_tiers'][0]['credits'] != NativeTypeTemplate(1, self.machine):
                raise AssertionError("First pricing_tier entry has to give exactly one credits.")
        except IndexError:
            price_per_game = 1

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

        self.debug_log("Calculated the credit unit to be %s based on a minimum"
                       "currency value of %s and a price per game of %s",
                       self.credit_unit, min_currency_value, price_per_game)

        self.credit_units_per_game = int(price_per_game / self.credit_unit)

        self.info_log("Credit units per game: %s", self.credit_units_per_game)

    def _calculate_pricing_tiers(self):
        # pricing tiers are calculated with a set of tuples which indicate the
        # credit units for the price break as well as the "bump" in credit
        # units that should be added once that break is passed.

        index = 0
        for pricing_tier in self.credits_config['pricing_tiers']:
            price = pricing_tier['price'].evaluate([])
            credit_units = price / self.credit_unit
            credits_in_tier = pricing_tier['credits'].evaluate([])
            actual_credit_units = self.credit_units_per_game * credits_in_tier
            bonus = actual_credit_units - credit_units

            self.machine.variables.set_machine_var("price_per_game_raw_{}".format(index), price)
            self.machine.variables.set_machine_var("price_per_game_string_{}".format(index),
                                                   self.credits_config['price_tier_template'].format(
                                                       price=price, credits=credits_in_tier))

            self.debug_log("Pricing Tier Bonus. Price: %s, Credits: %s. "
                           "Credit units for this tier: %s, Credit units this "
                           "tier buys: %s, Bonus bump needed: %s",
                           price, credits_in_tier,
                           credit_units, actual_credit_units, bonus)

            self.pricing_tiers.add((credit_units, bonus))
            index += 1

    def enable_credit_play(self, post_event=True, **kwargs):
        """Enable credits play."""
        del kwargs

        credit_units = self._get_credit_units()

        if self.credits_config['persist_credits_while_off_time']:
            self.machine.variables.configure_machine_var(name='credit_units', persist=True,
                                                         expire_secs=self.credits_config[
                                                             'persist_credits_while_off_time'])
        self.machine.variables.set_machine_var(name='credit_units', value=credit_units)

        '''machine_var: credit_units

        desc: How many credit units are on the machine. Note that credit units
        are not useful for display purposes since they represent the number of
        credits in a ration related to the lowest common denominator of the
        partial credit fraction. See the related *credits_string* and
        *credits_value* machine variables for more useful formats.
        '''

        self.machine.variables.set_machine_var('credits_string', ' ')
        # doc string is in machine.py for credits_string

        self.machine.settings.set_setting_value('free_play', False)

        self.machine.variables.set_machine_var('credits_value', '0')
        '''machine_var: credits_value

        desc: The human readable string form which shows the number value of
        how many credits are on the machine, including whole and fractional
        credits, for example "1" or "2 1/2" or "3 3/4".

        If you want the full string with the word "CREDITS" in it, use the
        "credits_string" machine variable.
        '''

        self.machine.variables.set_machine_var('credits_whole_num', 0)
        '''machine_var: credits_whole_num

        desc: The whole number portion of the total credits on the machine.
        For example, if the machine has 3 1/2 credits, this value is "3".
        '''

        self.machine.variables.set_machine_var('credits_numerator', 0)
        '''machine_var: credits_numerator

        desc: The numerator portion of the total credits on the machine.
        For example, if the machine has 4 1/2 credits, this value is "1".
        '''
        self.machine.variables.set_machine_var('credits_denominator', 0)
        '''machine_var: credits_whole_num

        desc: The denominator portion of the total credits on the machine.
        For example, if the machine has 4 1/2 credits, this value is "2".
        '''

        self._update_credit_strings()

        self._enable_credit_handlers()

        # prevent duplicate handlers
        self._remove_event_handlers()

        # setup event handlers
        self.add_mode_event_handler('player_add_request',
                                    self._player_add_request)
        self.add_mode_event_handler('request_to_start_game',
                                    self._request_to_start_game)
        self.add_mode_event_handler('player_added',
                                    self._player_added)
        self.add_mode_event_handler('mode_game_started',
                                    self._game_started)
        self.add_mode_event_handler('mode_game_stopped',
                                    self._game_ended)
        self.add_mode_event_handler('ball_starting',
                                    self._ball_starting)
        if post_event:
            self.machine.events.post('enabling_credit_play')
        '''event: enabling_credit_play
        desc: The game is no longer on free play. Credits are required to
        start a game. This event is also posted on MPF boot if the credits mode
         is enabled and the game is not set to free play.
        '''

    def _remove_event_handlers(self):
        """Remove event handlers."""
        self.machine.events.remove_handler(self._player_add_request)
        self.machine.events.remove_handler(self._request_to_start_game)
        self.machine.events.remove_handler(self._player_added)
        self.machine.events.remove_handler(self._game_ended)
        self.machine.events.remove_handler(self._game_started)
        self.machine.events.remove_handler(self._ball_starting)

    def enable_free_play(self, post_event=True, **kwargs):
        """Enable free play."""
        del kwargs
        self.machine.settings.set_setting_value('free_play', True)

        for index in range(len(self.credits_config['pricing_tiers'])):
            self.machine.variables.remove_machine_var("price_per_game_raw_{}".format(index))
            self.machine.variables.remove_machine_var("price_per_game_string_{}".format(index))

        self._remove_event_handlers()

        self._disable_credit_handlers()

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

        if self.machine.settings.get_setting_value('free_play'):
            self.enable_credit_play()
        else:
            self.enable_free_play()

    def _get_credit_units(self):
        credit_units = self.machine.variables.get_machine_var('credit_units')
        if not credit_units:
            credit_units = 0
        return credit_units

    def _player_add_request(self, **kwargs):
        del kwargs
        if (self._get_credit_units() >=
                self.credit_units_per_game):
            self.info_log("Received request to add player. Request Approved. Sufficient credits available.")
            return True

        self.info_log("Received request to add player. Request Denied. Not enough credits available.")
        self.machine.events.post("not_enough_credits")
        '''event: not_enough_credits
        desc: A player has pushed the start button, but the game is not set
        to free play and there are not enough credits to start a game or
        add a player.
        '''
        return False

    def _request_to_start_game(self, **kwargs):
        del kwargs
        if (self._get_credit_units() >=
                self.credit_units_per_game):
            self.info_log("Received request to start game. Request Approved. Sufficient credits available.")
            return True

        self.info_log("Received request to start game. Request Denied. Not enough credits available.")
        self.machine.events.post("not_enough_credits")
        # event docstring covered in _player_add_request() method
        return False

    def _player_added(self, **kwargs):
        del kwargs
        if self.machine.settings.get_setting_value('free_play'):
            self._audit_increment_non_coin(1, audit_class='4 Total Free Games')
        else:
            self._audit_increment_non_coin(1, audit_class='3 Total Paid Games')

            new_credit_units = (self._get_credit_units() -
                                self.credit_units_per_game)

            if new_credit_units < 0:
                self.warning_log("Somehow credit units went below 0?!? Resetting "
                                 "to 0.")
                new_credit_units = 0

            self.machine.variables.set_machine_var('credit_units', new_credit_units)
            self._update_credit_strings()
        total_paid = self._get_audit_non_coin('3 Total Paid Games')
        total_free = self._get_audit_non_coin('4 Total Free Games')
        total_all = total_paid + total_free
        free_percentage = "{:.2%}".format(total_free / total_all)
        paid_percentage = "{:.2%}".format(total_paid / total_all)
        self._audit_set_non_coin(free_percentage, audit_class='5 Free Games Percentage')
        self._audit_set_non_coin(paid_percentage, audit_class='6 Paid Games Percentage')

    def _enable_credit_handlers(self):
        for switch_settings in self.credits_config['switches']:
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch_settings['switch'],
                callback=self._credit_switch_callback,
                callback_kwargs={'value': switch_settings['value'].evaluate([]),
                                 'audit_class': switch_settings['type'],
                                 'key_name': switch_settings['label']})

        for switch in self.credits_config['service_credits_switch']:
            self.machine.switch_controller.add_switch_handler_obj(
                switch=switch,
                callback=self._service_credit_callback)

        for event_settings in self.credits_config['events']:
            self.machine.events.add_handler(
                event=event_settings['event'],
                handler=self._credit_event_callback,
                credits=event_settings['credits'],
                audit_class=event_settings['type'])

    def _disable_credit_handlers(self):
        for switch_settings in self.credits_config['switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch_settings['switch'].name,
                callback=self._credit_switch_callback)

        self.machine.events.remove_handler(self._credit_event_callback)

        for switch in self.credits_config['service_credits_switch']:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self._service_credit_callback)

    def _credit_switch_callback(self, value, audit_class, key_name):
        self.info_log("Credit switch hit. Credit Added. Value: %s. Type: %s keyName: %s", value, audit_class, key_name)
        self._add_credit_units(credit_units=value / self.credit_unit)
        self._audit(value, audit_class, key_name)
        self._reset_timeouts()

    # credits is a built-in in python
    # pylint: disable-msg=redefined-builtin
    def _credit_event_callback(self, credits, audit_class, **kwargs):
        credits_value = credits.evaluate(kwargs)
        self.info_log("Credit event hit. Credit Added. Credits: %s. Type: %s", credits_value, audit_class)
        self._add_credit_units(credit_units=credits_value * self.credit_units_per_game, price_tiering=False)
        self._audit(credits_value, audit_class)
        self._reset_timeouts()

    def _service_credit_callback(self):
        self.info_log("Service Credit Added. Value: 1.")
        self.add_credit(price_tiering=False)
        self._audit(1, 'service_credit')

    def _add_credit_units(self, credit_units, price_tiering=True):
        self.debug_log("Adding %s credit_units. Price tiering: %s",
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

        max_credit_units = (self.credits_config['max_credits'].evaluate([]) *
                            self.credit_units_per_game)

        if max_credit_units and total_credit_units > max_credit_units:
            self.info_log("Max credits reached.")
            self._update_credit_strings()
            self.machine.events.post('max_credits_reached')
            '''event: max_credits_reached
            desc: Credits have just been added to the machine, but the
            configured maximum number of credits has been reached.'''
            self.machine.variables.set_machine_var('credit_units', max_credit_units)

        if max_credit_units <= 0 or max_credit_units > previous_credit_units:
            self.info_log("Credit units added")
            self.machine.variables.set_machine_var('credit_units', total_credit_units)
            self._update_credit_strings()
            self.machine.events.post('credits_added')
            '''event: credits_added
            desc: Credits (or partial credits) have just been added to the
            machine.'''

    def add_credit(self, price_tiering=True):
        """Add a single credit to the machine.

        Args:
        ----
            price_tiering: Boolean which controls whether this credit will be
                eligible for the pricing tier bonuses. Default is True.

        """
        self._add_credit_units(self.credit_units_per_game, price_tiering)

    def _reset_pricing_tier_credits(self):
        if not self.reset_pricing_tier_count_this_game:
            self.info_log("Resetting pricing tier credit count.")
            self.credit_units_for_pricing_tiers = 0
            self.reset_pricing_tier_count_this_game = True

    def _ball_starting(self, player, ball, **kwargs):
        del kwargs
        if player == 1 and ball == 2:
            self._reset_pricing_tier_credits()

    def _set_free_play_string(self):
        display_string = self.credits_config['free_play_string']
        self.machine.variables.set_machine_var('credits_string', display_string)

    def _update_credit_strings(self):
        if self.machine.settings.get_setting_value('free_play'):
            self._set_free_play_string()
            return

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

        display_string = '{} {}'.format(self.credits_config['credits_string'], display_fraction)
        self.machine.variables.set_machine_var('credits_string', display_string)
        self.machine.variables.set_machine_var('credits_value', display_fraction)
        self.machine.variables.set_machine_var('credits_whole_num', whole_num)
        self.machine.variables.set_machine_var('credits_numerator', numerator)
        self.machine.variables.set_machine_var('credits_denominator', denominator)

    def _get_audit_non_coin(self, audit_class):
        if audit_class not in self.earnings:
            self.earnings[audit_class] = dict()
            self.earnings[audit_class] = 0
        return self.earnings[audit_class]

    def _audit_increment_non_coin(self, value, audit_class):
        # create file if it does not exist
        if audit_class not in self.earnings:
            self.earnings[audit_class] = dict()
            self.earnings[audit_class] = value
        else:
            self.earnings[audit_class] += value
        self.data_manager.save_all(data=self.earnings)

    def _audit_set_non_coin(self, value, audit_class):
        # create file if it does not exist
        if audit_class not in self.earnings:
            self.earnings[audit_class] = dict()
        self.earnings[audit_class] = value
        self.data_manager.save_all(data=self.earnings)

    def _audit(self, value, audit_class, key_name=None):
        self.info_log("Credit audits. Value: %s. Type: %s keyName: %s", value, audit_class, key_name)
        # increment default audits
        one = '1 Total Coins ' + audit_class
        if one not in self.earnings:
            self.earnings[one] = 1
        else:
            self.earnings[one] += 1

        two = '2 Total Earnings ' + audit_class
        if two not in self.earnings:
            self.earnings[two] = value
        else:
            self.earnings[two] += value

        # increment keyed audits
        if key_name is not None:
            key_count = key_name + ' Coins ' + audit_class
            if key_count not in self.earnings:
                self.earnings[key_count] = 1
            else:
                self.earnings[key_count] += 1

            key_val = key_name + ' Earnings ' + audit_class
            if key_val not in self.earnings:
                self.earnings[key_val] = value
            else:
                self.earnings[key_val] += value

        self.data_manager.save_all(data=self.earnings)

    def _game_started(self, **kwargs):
        del kwargs
        self.debug_log("Removing credit clearing delays.")
        self.delay.remove('clear_fractional_credits')
        self.delay.remove('clear_all_credits')

    def _reset_timeouts(self):
        if self.credits_config['fractional_credit_expiration_time']:
            self.debug_log("Adding delay to clear fractional credits")
            self.delay.reset(
                ms=self.credits_config['fractional_credit_expiration_time'],
                callback=self._clear_fractional_credits,
                name='clear_fractional_credits')

        if self.credits_config['credit_expiration_time']:
            self.debug_log("Adding delay to clear credits")
            self.delay.reset(
                ms=self.credits_config['credit_expiration_time'],
                callback=self.clear_all_credits,
                name='clear_all_credits')

    def _game_ended(self, **kwargs):
        del kwargs
        self._reset_timeouts()

        self.reset_pricing_tier_count_this_game = False

    def _clear_fractional_credits(self):
        self.info_log("Clearing fractional credits.")

        credit_units = self._get_credit_units()
        credit_units -= credit_units % self.credit_units_per_game

        self.machine.variables.set_machine_var('credit_units', credit_units)
        self._update_credit_strings()

    def clear_all_credits(self, **kwargs):
        """Clear all credits."""
        del kwargs
        self.info_log("Clearing all credits.")
        self.machine.variables.set_machine_var('credit_units', 0)
        self._update_credit_strings()
