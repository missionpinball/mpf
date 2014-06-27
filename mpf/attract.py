# attract.py
# This is our attract mode

import logging
import mpf.tasks
import mpf.machine_mode


class Attract(mpf.machine_mode.MachineMode):

    def __init__(self, machine):
        super(Attract, self).__init__(machine)
        self.log = logging.getLogger("Attract Mode")

    def start(self):
        super(Attract, self).start()
        # register event handlers
        self.registered_event_handlers.append(
            self.machine.events.add_handler('sw_start',
            self.start_button_pressed))

    def start_button_pressed(self):
        # test for active?
        # todo should this be a decorator?
        self.log.debug("Received start button press")
        self.machine.events.post('request_to_start_game', ev_type='boolean',
                                 callback=self.result_of_start_request)

    def result_of_start_request(self, result=True):
        """ If we can start a game, we advance the machine flow.
        """
        if result is False:
            self.log.debug("Game start was denied")
        else:  # else because we want to start on True *or* None
            self.log.debug("Let's start a game!!")
            self.machine.events.post('machine_flow_advance')
            # machine flow will move on to the next mode when this mode ends

    def tick(self):
        while self.active:
            # do something here
            yield
