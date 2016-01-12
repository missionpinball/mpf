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
                self.iterator = iter(self.callbacks)
                element = next(self.iterator)
                timeout = self.playfield.config['ball_search_wait_after_iteration']
                # TODO: give up at some point? implement actions

            (priority, callback) = element
            # if a callback returns True we wait for the next one
            if callback(self.iteration):
                self.delay.add(name='run', callback=self.run, ms=timeout)
                return

