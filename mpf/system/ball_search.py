"""Implements the ball search procedure"""

import logging

from mpf.system.tasks import DelayManager
from mpf.system.utility_functions import Util

class BallSearch(object):

    def __init__(self, machine, playfield):
        self.machine = machine
        self.playfield = playfield
        self.log = logging.getLogger("BallSearch " + playfield.name)
        self.delay = DelayManager(self.machine.delayRegistry)

        self.started = False
        self.enabled = False
        self.callbacks = []

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)


    def request_to_start_game(self):
        """Method registered for the *request_to_start_game* event.

        Returns false if the ball search is running.
        """
        if self.started:
            return False
        else:
            return

    def register(self, priority, callback):
        self.callbacks.append((priority, callback))
        # sort by priority
        self.callbacks = sorted(self.callbacks, key=lambda entry: entry[0])

    def enable(self):
        if not self.playfield.config['enable_ball_search']:
            return

        if not self.callbacks:
            raise AssertionError("No callbacks registered")

        self.log.debug("Enabling Ball Search")

        self.enabled = True
        self.reset_timer()

    def disable(self):
        self.started = False
        self.enabled = False
        self.delay.remove('start')
        self.delay.remove('run')

    def reset_timer(self):
        if self.enabled and not self.started:
            self.delay.reset(name='start', callback=self.start, ms=self.playfield.config['ball_search_timeout'])

    def start(self):
        self.started = True
        self.iteration = 1
        self.iterator = iter(self.callbacks)
        self.log.info("Starting ball search")
        self.run()
        
    def run(self):
        timeout = self.playfield.config['ball_search_interval']
        # iterate until we are done with all callbacks
        while True:
            try:
                element = next(self.iterator)
            except StopIteration:
                self.iteration += 1
                # give up at some point
                if self.iteration > self.playfield.config['ball_search_iterations']:
                    self.give_up()
                    return

                self.log.info("Ball Search iteration %s", self.iteration)
                self.iterator = iter(self.callbacks)
                element = next(self.iterator)
                timeout = self.playfield.config['ball_search_wait_after_iteration']

            (priority, callback) = element
            # if a callback returns True we wait for the next one
            if callback(self.iteration):
                self.delay.add(name='run', callback=self.run, ms=timeout)
                return

    def give_up(self):
        self.log.warning("Ball Search failed to find ball. Giving up!")
        self.disable()

        self.playfield.balls = 0
        self.machine.ball_controller.num_balls_known -= 1

        if self.playfield.config['ball_search_failed_action'] == "new_ball":
            self.log.info("Adding a replacement ball")
            self.playfield.add_ball()
        elif self.playfield.config['ball_search_failed_action'] == "end_game":
            if self.machine.game:
                self.log.info("Ending the game")
                self.machine.game.game_ending()
            else:
                self.log.info("There is no game. Doing nothing!")
        else:
            raise AssertionError("Unknown action " + self.playfield.config['ball_search_failed_action'])
