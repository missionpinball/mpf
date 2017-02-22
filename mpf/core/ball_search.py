"""Implements the ball search procedure."""

from mpf.core.delays import DelayManager
from mpf.core.mpf_controller import MpfController


class BallSearch(MpfController):

    """Ball search controller."""

    def __init__(self, machine, playfield):
        """Initialize ball search."""
        self.module_name = 'BallSearch.' + playfield.name
        self.config_name = 'ball_search'

        super().__init__(machine)

        self.playfield = playfield

        self.delay = DelayManager(self.machine.delayRegistry)

        self.started = False
        self.enabled = False
        self.blocked = False
        self.callbacks = []

        self.iteration = False
        self.iterator = False
        self.phase = False

        self.ball_search_control_handlers = list()

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)

        self.machine.events.add_handler('cancel_ball_search',
                                        self.cancel_ball_search)
        '''event: cancel_ball_search
        desc: This event will cancel all running ball searches and mark the
        balls as lost. This is only a handler so all you have to do is to post
        the event.'''

    def request_to_start_game(self, **kwargs):
        """Method registered for the *request_to_start_game* event.

        Prevents the game from starting while ball search is running.

        """
        # todo we should enable ball search if a ball is missing on game start

        del kwargs
        if self.started:
            return False
        else:
            return

    def register(self, priority, callback, name):
        """Register a callback for sequential ball search.

        Callbacks are called by priority. Ball search only waits if the
        callback returns true.

        Args:
            priority: priority of this callback in the ball search procedure
            callback: callback to call. ball search will wait before the next
                callback, if it returns true
            name: string name which is used for debugging & the logs
        """
        self.debug_log("Registering callback: {} (priority: {})".format(
            name, priority))
        self.callbacks.append((priority, callback, name))
        # sort by priority
        self.callbacks = sorted(self.callbacks, key=lambda entry: entry[0])

    def enable(self, **kwargs):
        """Enable but do not start ball search.

        Ball search is started by a timeout. Enable also resets that timer.
        """
        if self.blocked:
            return

        del kwargs
        if self.playfield.config['enable_ball_search'] is False or (
            not self.playfield.config['enable_ball_search'] and
                not self.machine.config['mpf']['default_ball_search']):
            return

        if not self.callbacks:
            raise AssertionError("No callbacks registered")

        self.debug_log("Enabling Ball Search")

        self.enabled = True

        self.reset_timer()

    def disable(self, **kwargs):
        """Disable ball search.

        Will stop the ball search if it is running.
        """
        del kwargs
        self.stop()

        self.debug_log("Disabling Ball Search")
        self.enabled = False
        self.delay.remove('start')

    def block(self, **kwargs):
        """Block ball search for this playfield.

        Blocking will disable ball search if it's enabled or running, and will
        prevent ball search from enabling if it's disabled until
        ball_search_unblock() is called.
        """
        del kwargs
        self.debug_log("Blocking ball search")
        self.disable()
        self.blocked = True

    def unblock(self, **kwargs):
        """Unblock ball search for this playfield.

        This will check to see if there are balls on the playfield, and if so,
        enable ball search.
        """
        del kwargs
        self.debug_log("Unblocking ball search")
        self.blocked = False

        if self.playfield.balls:
            self.enable()

    def reset_timer(self):
        """Reset the timer to start ball search.

        This also cancels an active running ball search.

        This is called by the playfield anytime a playfield switch is hit.

        """
        if self.started:
            self.stop()

        if self.enabled:
            self.debug_log("Resetting ball search timer")
            self.delay.reset(name='start', callback=self.start,
                             ms=self.playfield.config['ball_search_timeout'])

    def start(self):
        """Actually start ball search."""
        if not self.enabled or self.started or not self.callbacks:
            return
        self.started = True
        self.iteration = 1
        self.phase = 1
        self.iterator = iter(self.callbacks)
        self.info_log("Starting ball search")
        self.machine.events.post('ball_search_started')
        '''event: ball_search_started

        desc: The ball search process has been begun.
        '''
        self._run()

    def stop(self):
        """Stop an active running ball search."""
        if not self.started:
            return

        self.debug_log("Stopping ball search")

        self.started = False
        self.delay.remove('run')

        self.machine.events.post('ball_search_stopped')
        '''event: ball_search_stopped

        desc: The ball search process has been disabled. This event is posted
            any time ball search stops, regardless of whether it found a ball
            or gave up. (If the ball search failed to find the ball, it will
            also post the *ball_search_failed* event.)
        '''

    def _run(self):
        # Runs one iteration of the ball search.
        # Will schedule itself for the next run.

        timeout = self.playfield.config['ball_search_interval']

        # iterate until we are done with all callbacks
        while True:
            try:
                element = next(self.iterator)
            except StopIteration:
                self.iteration += 1
                # give up at some point
                if self.iteration > self.playfield.config[
                        'ball_search_phase_{}_searches'.format(self.phase)]:
                    self.phase += 1
                    self.iteration = 1
                    if self.phase > 3:
                        self.give_up()
                        return

                self.iterator = iter(self.callbacks)
                element = next(self.iterator)
                timeout = self.playfield.config[
                    'ball_search_wait_after_iteration']

            (dummy_priority, callback, name) = element
            # if a callback returns True we wait for the next one
            self.debug_log("Ball search: {} (phase: {}  iteration: {})".format(
                           name, self.phase, self.iteration))
            if callback(self.phase, self.iteration):
                self.delay.add(name='run', callback=self._run, ms=timeout)
                return

    def cancel_ball_search(self, **kwargs):
        """Cancel the current ball search and mark the ball as missing."""
        del kwargs
        if self.started:
            self.give_up()

    def give_up(self):
        """Give up the ball search.

        Did not find the missing ball. Execute the failed action which either
        adds a replacement ball or ends the game.
        """
        self.info_log("Ball Search failed to find ball. Giving up!")
        self.disable()
        self.machine.events.post('ball_search_failed')
        '''event: ball_search_failed

        desc: The ball search process has failed to locate a missing or stuck
            ball and has given up. This event will be posted immediately after
            the *ball_search_stopped* event.
        '''

        lost_balls = self.playfield.balls
        self.machine.ball_controller.num_balls_known -= lost_balls
        self.playfield.balls = 0
        self.playfield.available_balls = 0

        self._compensate_lost_balls(lost_balls)

    def _compensate_lost_balls(self, lost_balls):
        if not self.machine.game:
            return

        if self.playfield.config['ball_search_failed_action'] == "new_ball":
            if self.machine.ball_controller.num_balls_known > 0:
                # we have at least one ball remaining
                self.info_log("Adding %s replacement ball", lost_balls)
                for dummy_iterator in range(lost_balls):
                    self.playfield.add_ball()
            else:
                self.info_log("No more balls left. Ending game!")
                self.machine.game.game_ending()

        elif self.playfield.config['ball_search_failed_action'] == "end_game":
            if self.machine.game:
                self.info_log("Ending the game")
                self.machine.game.game_ending()
            else:
                self.warning_log("There is no game. Doing nothing!")
        else:
            raise AssertionError("Unknown action " + self.playfield.config[
                'ball_search_failed_action'])
