# machine_mode.py
import logging
import mpf.tasks
import mpf.events


class MachineMode(object):
    """ A machine mode represents as pecial modes, the idea is there's only
    one at a time.

    You can specify an order so that when one ends, the next one starts.

    Examples:
    Attract
    Game
    Match
    Highscore Entry
    Service

    The idea is the machine modes will control the buttons since they do
    different things in different modes. ("Buttons" versus "Switches" in this
    case. Buttons are things that players can control, like coin switches,
    control panel buttons, flippers, start, plunge, etc.)
    """

    def __init__(self, machine):
        self.log = logging.getLogger(__name__)
        self.machine = machine
        self.task = None
        self.delays = mpf.tasks.DelayManager()
        self.registered_event_handlers = []

    def start(self):
        """ Starts this machine mode. """
        self.log.info("Mode started")
        self.active = True
        self.task = mpf.tasks.Task.Create(self.tick, sleep=0)

    def stop(self):
        """ Stops this machine mode. """

        self.log.debug("Stopping...")
        self.ative = False
        # clear delays
        self.log.debug("Removing scheduled delays")
        self.delays.clear()

        # deregister event handlers
        self.log.debug("Removing event handlers")
        for handler in self.registered_event_handlers:
            self.machine.events.remove_handler(handler)
        self.log.debug("Stopped")

    def tick(self):
        """ Most likely you'll just copy this entire method to your mode
        subclass. No need for super().
        """
        while self.active:
            # do something here
            yield
