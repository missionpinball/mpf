"""Implements the ball search procedure."""

from mpf.core.delays import DelayManager
from mpf.core.mpf_controller import MpfController


class BallSearch(MpfController):

    """Ball search controller."""

    def __init__(self, machine, playfield):
        """Initialise ball search."""

        self.module_name = 'BallSearch.' + playfield.name
        self.config_name = 'ball_search'

        super().__init__(machine)

        self.playfield = playfield

        self.delay = DelayManager(self.machine.delayRegistry)

        self.started = False
        self.enabled = False
        self.callbacks = []

        self.iteration = False
        self.iterator = False
        self.phase = False

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)

        self.machine.events.add_handler('cancel_ball_search',
                                        self.cancel_ball_search)
        '''event: cancel_ball_search
        desc: This event will cancel all running ball searches and mark the balls as lost. This is only a handler
        so all you have to do is to post the event.'''

    def request_to_start_game(self, **kwargs):
        """Method registered for the *request_to_start_game* event.

        Returns false if the ball search is running.
        """
        del kwargs
        if self.started:
            return False
        else:
            return

    def register(self, priority, callback):
        """Register a callback for sequential ballsearch.

        Callbacks are called by priority. Ball search only waits if the callback returns true.

        Args:
            priority: priority of this callback in the ball search procedure
            callback: callback to call. ball search will wait before the next callback, if it returns true
        """
        self.callbacks.append((priority, callback))
        # sort by priority
        self.callbacks = sorted(self.callbacks, key=lambda entry: entry[0])

    def enable(self):
        """Enable but do not start ball search.

        Ball search is started by a timeout. Enable also resets that timer.
        """
        if self.playfield.config['enable_ball_search'] is False or (
            not self.playfield.config['enable_ball_search'] and not self.machine.config['mpf']['default_ball_search']
        ):
            return

        if not self.callbacks:
            raise AssertionError("No callbacks registered")

        self.debug_log("Enabling Ball Search")

        self.enabled = True
        self.reset_timer()

    def disable(self):
        """Disable ball search.

        Will stop the ball search if it is running.
        """
        if self.started:
            self.machine.events.post('ball_search_stopped')
        '''event: ball_search_stopped

        desc: The ball search process has been disabled. This event is posted
            any time ball search stops, regardless of whether it found a ball
            or gave up. (If the ball search failed to find the ball, it will
            also post the *ball_search_failed* event.)
        '''

        self.debug_log("Disabling Ball Search")

        self.started = False
        self.enabled = False
        self.delay.remove('start')
        self.delay.remove('run')

    def reset_timer(self):
        """Reset the start timer.

        Called by playfield.
        """
        if self.enabled and not self.started:
            self.delay.reset(name='start', callback=self.start, ms=self.playfield.config['ball_search_timeout'])

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
        self.run()

    def run(self):
        """Run one iteration of the ball search.

        Will schedule itself for the next run.
        """
        timeout = self.playfield.config['ball_search_interval']
        # iterate until we are done with all callbacks
        while True:
            try:
                element = next(self.iterator)
            except StopIteration:
                self.iteration += 1
                # give up at some point
                if self.iteration > self.playfield.config['ball_search_phase_' + str(self.phase) + '_searches']:
                    self.phase += 1
                    self.iteration = 1
                    if self.phase > 3:
                        self.give_up()
                        return

                self.debug_log("Ball Search Phase %s Iteration %s", self.phase, self.iteration)
                self.iterator = iter(self.callbacks)
                element = next(self.iterator)
                timeout = self.playfield.config['ball_search_wait_after_iteration']

            (dummy_priority, callback) = element
            # if a callback returns True we wait for the next one
            if callback(self.phase, self.iteration):
                self.delay.add(name='run', callback=self.run, ms=timeout)
                return

    def cancel_ball_search(self, **kwargs):
        """Cancel the current ballsearch and mark the ball as missing."""
        del kwargs
        if self.started:
            self.give_up()

    def give_up(self):
        """Give up the ball search.

        Did not find the missing ball. Execute the failed action which either adds a replacement ball or ends the game.
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
            raise AssertionError("Unknown action " + self.playfield.config['ball_search_failed_action'])
