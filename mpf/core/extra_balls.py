"""Class for the ExtraBallController"""
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.mpf_controller import MpfController


class ExtraBallController(MpfController):
    """Tracks and manages extra balls at the global level."""

    config_name = 'extra_balls'

    def __init__(self, machine):
        """Initialize ExtraBallManager"""
        super().__init__(machine)

        self.extra_balls = CaseInsensitiveDict()

        self.config = self.machine.config_validator.validate_config(
            config_spec='global_extra_ball_settings',
            source=self.machine.config['global_extra_ball_settings'])

        self.enabled = self.config['enabled']

        self.events_only = self.config['events_only']

        self.machine.events.add_handler('player_add_success',
                                        self._player_added)
        self.machine.events.add_handler('player_turn_start',
                                        self._player_turn_start)
        self.machine.events.add_handler('player_turn_stop',
                                        self._player_turn_stop)
        self.machine.events.add_handler('award_extra_ball',
                                        self.award)
        '''event: award_extra_ball

        desc: This is an event you can post which will immediately award the
        player an extra ball (assuming they're within the limits of max
        extra balls, etc.). This event will in turn post the
        extra_ball_awarded event if the extra ball is able to be awarded.

        Note that if you want to just light the extra ball, but not award it
        right away, then use the :doc:`award_lit_extra_ball` event instead.

        Also note that if an extra ball is lit, this event will NOT unlight
        or decrement the lit extra ball count. If you want to do that, use the
        :doc:`award_lit_extra_ball` instead.

        '''
        self.machine.events.add_handler('award_lit_extra_ball',
                                        self.award_lit)
        '''event: award_lit_extra_ball

        desc: This event will award an extra ball if extra ball is lit. If the
        player has no lit extra balls, then this event will have no effect.

        This is a good event to use in your extra ball mode or shot to post
        to collect the lit extra ball. It will in turn post the
        :doc:`extra_ball_awarded` event (assuming the player has not
        exceeded any configured limits for max extra balls).

        If you just want to award an extra ball regardless of whether the
        player has one lit, use the :doc:`award_extra_ball` event instead.

        '''

        self.machine.events.add_handler('light_extra_ball',
                                        self.light)

        '''event: light_extra_ball

        This event will check to make sure the extra ball lit limits are not
        exceeded, and then add an extra ball lit count to the player, and then
        post the :doc:`extra_ball_lit` event.

        Note that MPF tracks the number of lit extra balls, so if you post
        this event twice then the player will be able to collect two extra
        balls (one at a time) by you posting the :doc:`award_extra_ball`
        event.

        '''

    def _player_added(self, player, **kwargs):
        del kwargs

        player.extra_balls_awarded = dict()
        player.extra_balls_lit = 0
        player.extra_balls = 0
        player.extra_balls_current_ball = 0

    def _player_turn_start(self, player, **kwargs):
        del kwargs

        if not self.enabled:
            return

        player.extra_balls_current_ball = 0

        if player.extra_balls_lit:
            self.relight()

    def _player_turn_stop(self, player, **kwargs):
        del kwargs

        if not self.config['lit_memory']:
            player.extra_balls_lit = 0

    def award_lit(self, **kwargs):
        """Awards a lit extra ball.

        If the player does not have any lit extra balls, this method does
        nothing."""
        del kwargs

        try:
            player = self.machine.game.player
        except AttributeError:
            return

        if not self.enabled:
            self._extra_ball_disabled_award()
            return

        if not player.extra_balls_lit:
            return

        player.extra_balls_lit -= 1
        self.award()

        if not player.extra_balls_lit:
            self.machine.events.post('extra_ball_unlit')

        '''event: extra_ball_unlit

        desc: No more lit extra balls are available. This is a good event to
        use as a stop event for your extra ball lit mode or whatever you're
        using to indicate to the player that an extra ball is available.

        '''

    def award(self, **kwargs):
        """Immediately awards an extra ball.

        This event first checks to make sure the limits of the max extra
        balls have not been exceeded.
        """
        del kwargs

        try:
            player = self.machine.game.player
        except AttributeError:
            return

        if not self.enabled:
            self._extra_ball_disabled_award()
            return

        if (self.config['max_per_ball'] and
                player.extra_balls_this_ball >= self.config['max_per_ball']):
            self.machine.events.post('extra_ball_max_exceeded')
            '''event: extra_ball_max_exceeded

            desc: The global configured max extra balls (either for this
            ball or total for the game for this player has been exceeded, so
            this event is posted instead of the extra_ball_awarded event.

            '''

        elif (self.config['max_per_game'] and
                player.extra_balls_awarded >= self.config['max_per_game']):
            self.machine.events.post('extra_ball_max_exceeded')

        else:
            self.machine.events.post('extra_ball_awarded')
            '''event: extra_ball_awarded

            desc: An extra ball was just awarded. This is a good event to
            use to trigger award shows, sounds, etc.

            '''

            if not self.events_only:
                player.extra_balls += 1

    def light(self, **kwargs):
        """Lights the extra ball.

        This method also increments the player's extra_balls_lit count.
        """
        del kwargs

        try:
            player = self.machine.game.player
        except AttributeError:
            return

        if not self.enabled:
            return

        if ((self.config['max_lit'] and
                player.extra_balls_lit < self.config['max_lit']) or
                not self.config['max_lit']):

            player.extra_balls_lit += 1
            self.machine.events.post('extra_ball_lit')
            '''event: extra_ball_lit

            desc: An extra ball was just lit. This is a good event to use to
            start your extra ball lit mode, or to turn on an extra ball light,
            etc.

            Note that this event is posted if an extra ball is lit during play
            and also when a player's turn starts if they have a lit extra ball.

            See also the :doc:`extra_ball_lit_awarded` for a similar event that
            is only posted when an extra ball is lit during play, and not
            if the player starts their turn with the extra ball lit.

            '''

            self.machine.events.post('extra_ball_lit_awarded')
            '''event: extra_ball_lit_awarded

            desc: This even is posted when an extra ball is lit during play.
            It is NOT posted when a player's turn starts if they have a lit
            extra ball from their previous turn. Therefore this event is a
            good event to use for your award slides and shows when a player
            lights the extra ball, because you don't want to use
            :doc:`extra_ball_lit` because that is also posted when the
            player's turn starts and you don't want the award show to play
            again when they're starting their turn.

            '''

        else:
            self.machine.events.post('extra_ball_lit_max_exceeded')
            '''event: extra_ball_lit_max_exceeded

            desc: Posted when an extra ball would be lit, except there's a
            global configured max lit setting and the number of lit extra
            balls is higher than that.

            '''

    def relight(self, **kwargs):
        """Relights the extra ball when a player's turn starts.

        This event does not post the "extra_ball_lit_awarded" event so you
        can use it to not show the extra ball awards when a player starts
        their turn with an extra ball lit.
        """
        del kwargs

        try:
            player = self.machine.game.player
        except AttributeError:
            return

        if not self.enabled or not player.extra_balls_lit:
            return

        self.machine.events.post('extra_ball_lit')

    def _extra_ball_disabled_award(self):
        self.machine.events.post('extra_ball_disabled_award')
        '''event: extra_ball_disabled_award

        desc: Posted when you have the global extra ball settings set to not
        enable extra balls but where an extra ball would have been awarded.
        This is a good alternative event to use to score points or whatever
        else you want to give the player when extra balls are disabled.

        '''
