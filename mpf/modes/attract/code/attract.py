"""Contains the Attract class which is the attract mode in a pinball machine."""

from mpf.core.mode import Mode


class Attract(Mode):

    """Default mode running in a machine when a game is not in progress.

    Its main job is to watch for the start button to be pressed, to
    post the requests to start games, and to move the machine flow to the next
    mode if the request to start game comes back as approved.
    """

    def __init__(self, machine, config, name, path):
        """Initialise mode."""
        super().__init__(machine, config, name, path)

        self.start_button_pressed_time = 0.0
        self.start_hold_time = 0.0
        self.start_buttons_held = list()

    def mode_start(self, **kwargs):
        """Automatically called when the Attract game mode becomes active."""
        # register switch handlers for the start button press so we can
        # capture long presses

        # add these to the switch_handlers set so they'll be removed

        for switch in self.machine.switches.items_tagged(
                self.machine.config['game']['start_game_switch_tag']):
            self.switch_handlers.append(
                self.machine.switch_controller.add_switch_handler(
                    switch.name, self.start_button_pressed, 1))
            self.switch_handlers.append(
                self.machine.switch_controller.add_switch_handler(
                    switch.name, self.start_button_released, 0))

        if hasattr(self.machine, 'ball_devices'):
            self.machine.ball_controller.collect_balls()

        self.machine.events.post('enable_volume_keys')
        # move volume to its own mode?
        # todo

    def start_button_pressed(self):
        """Called when the a switch tagged with *start* is activated."""
        self.start_button_pressed_time = self.machine.clock.get_time()

    def start_button_released(self):
        """Called when the a switch tagged with *start* is deactivated.

        Since this is the Attract mode, this method posts a boolean event
        called *request_to_start_game*. If that event comes back True, this
        method calls :meth:`result_of_start_request`.
        """
        self.start_hold_time = self.machine.clock.get_time() - self.start_button_pressed_time
        self.start_buttons_held = list()

        for switch in self.machine.switches.items_tagged('player'):
            if self.machine.switch_controller.is_active(switch.name):
                self.start_buttons_held.append(switch.name)

        # todo test for active?
        self.machine.events.post_boolean('request_to_start_game',
                                         callback=self.result_of_start_request)
        '''event: request_to_start_game
        desc: This event is posted when to start a game. This is a boolean
        event. Any handler can return *False* and the game will not be
        started. Otherwise when this event is done, a new game is started.

        Posting this event is the only way to start a game in MPF, since many
        systems have to "approve" the start. (Are the balls in the right
        places, are there enough credits, etc.)
        '''

    def result_of_start_request(self, ev_result=True):
        """Called after the *request_to_start_game* event is posted.

        If `result` is True, this method posts the event
        *game_start*. If False, nothing happens, as the game start
        request was denied by some handler.

        Args:
            ev_result : Bool result of the boolean event
                *request_to_start_game.* If any registered event handler did not
                want the game to start, this will be False. Otherwise it's True.
        """
        if ev_result is False:
            self.log.debug("Game start was denied")
        else:  # else because we want to start on True *or* None
            self.log.debug("Let's start a game!!")
            self.machine.events.post('game_start',
                                     buttons=self.start_buttons_held,
                                     hold_time=self.start_hold_time)
            '''event: game_start
            desc: A game is starting. (Do not use this event to start a game.
            Instead, use the *request_to_start_game* event.

            args:
            buttons: A list of switches tagged with *player* that were held in
            when the start button was released. This is used for "alternate"
            game starts (e.g. hold the right flipper and press start for
            tournament mode, etc.)

            hold_time: The time, in seconds, that the start button was held in
            to start the game. This can be used to start alternate games via a
            "long press" of the start button.
            '''
