"""Implements the ball search procedure."""
from collections import namedtuple

from typing import List

from mpf.core.delays import DelayManager
from mpf.core.machine import MachineController
from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.playfield import Playfield

BallSearchCallback = namedtuple("BallSearchCallback", ["priority", "callback", "name"])


class BallSearch(MpfController):

    """Implements Ball search for a playfield device.

    In MPF, the ball search functionality is attached to each playfield
    device, rather than being done at the global level. (In other words, each
    playfield is responsible for making sure no balls get stuck on it, and it
    leverages an instance of this BallSearch class to handle it.)

    """

    def __init__(self, machine: MachineController, playfield: "Playfield") -> None:
        """Initialize ball search."""
        self.module_name = 'BallSearch.' + playfield.name
        self.config_name = 'ball_search'

        super().__init__(machine)

        self.playfield = playfield
        """The playfield device this ball search instance is attached to."""

        self.delay = DelayManager(self.machine.delayRegistry)

        self.started = False
        """Is the ball search process started (running) now."""
        self.enabled = False
        """Is ball search enabled."""
        self.blocked = False
        """If True, ball search will be blocked and will not start."""
        self.callbacks = []     # type: List[BallSearchCallback]

        self.iteration = False
        """Current iteration of the ball search, or ``False`` if ball search
        is not started."""
        self.iterator = False
        self.phase = False
        """Current phase of the ball search, or ``False`` if ball search is not
        started."""

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
        """Handle result of the *request_to_start_game* event.

        If ball search is running, this method will return *False* to prevent
        the game from starting while ball search is running.

        This method also posts the *ball_search_prevents_game_start* event
        if ball search is started.

        """
        # todo we should enable ball search if a ball is missing on game start

        del kwargs
        if self.started:

            self.machine.events.post('ball_search_prevents_game_start')
            '''event: ball_search_prevents_game_start
            desc: A game start has been requested, but the ball search process
            is running and thus the game start has been blocked. This is a
            good event to use for a slide player to inform the player that the
            machine is looking for a missing ball.'''

            return False
        else:
            return True

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
        self.callbacks.append(BallSearchCallback(priority, callback, name))
        # sort by priority
        self.callbacks = sorted(self.callbacks, key=lambda entry: entry.priority)

    def enable(self, **kwargs):
        """Enable the ball search for this playfield.

        Note that this method does *not* start the ball search process. Rather
        it just resets and starts the timeout timer, as well as resetting it
        when playfield switches are hit.

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

        This method will also stop the ball search if it is running.
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
        ``ball_search_unblock()`` is called.
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
        """Reset the timeout timer which starts ball search.

        This method will also cancel an actively running (started) ball search.

        This is called by the playfield anytime a playfield switch is hit.

        """
        if self.started:
            self.stop()

        if self.enabled:
            self.debug_log("Resetting ball search timer")
            self.delay.reset(name='start', callback=self.start,
                             ms=self.playfield.config['ball_search_timeout'])

    def start(self):
        """Start ball search the ball search process."""
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

        self.machine.events.post('ball_search_phase_1', iteration=1)
        # see description below

        self._run()

    def stop(self):
        """Stop an actively running ball search."""
        if not self.started:
            return

        self.info_log("Stopping ball search")

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
                self.machine.events.post('ball_search_phase_{}'.format(self.phase),
                                         iteration=self.iteration)
                '''event: 'ball_search_phase_(num)

                desc: The ball search phase (num) has started.
                args:
                    iteration: Current iteration of phase (num)
                '''
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

            # if a callback returns True we wait for the next one
            self.debug_log("Ball search: {} (phase: {}  iteration: {})".format(
                element.name, self.phase, self.iteration))
            if element.callback(self.phase, self.iteration):
                self.delay.add(name='run', callback=self._run, ms=timeout)
                return

    def cancel_ball_search(self, **kwargs):
        """Cancel the current ball search and mark the ball as missing."""
        del kwargs
        if self.started:
            self.give_up()

    def give_up(self):
        """Give up the ball search.

        This method is called when the ball search process Did not find the
        missing ball. It executes the failed action which depending on the specification of *ball_search_failed_action*,
        either adds a replacement ball, ends the game, or ends the current ball.
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
                self.machine.game.end_game()

        elif self.playfield.config['ball_search_failed_action'] == "end_game":
            if self.machine.game:
                self.info_log("Ending the game")
                self.machine.game.end_game()
            else:
                self.warning_log("There is no game. Doing nothing!")

        elif self.playfield.config['ball_search_failed_action'] == "end_ball":
            self.info_log("Ending current ball")
            self.machine.game.end_ball()

        else:
            raise AssertionError("Unknown action " + self.playfield.config[
                'ball_search_failed_action'])
