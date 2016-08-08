"""Mode timers."""
import logging

from mpf.core.delays import DelayManager


# pylint: disable-msg=too-many-instance-attributes
class ModeTimer(object):

    """Parent class for a mode timer.

    Args:
        machine: The main MPF MachineController object.
        mode: The parent mode object that this timer belongs to.
        name: The string name of this timer.
        config: A Python dictionary which contains the configuration settings
            for this timer.

    """

    def __init__(self, machine, mode, name, config):
        """Initialise mode timer."""
        self.machine = machine
        self.mode = mode
        self.name = name
        self.config = config

        if mode.player is None:
            raise AssertionError("Cannot use ModeTimer in mode without player.")

        self.tick_var = self.mode.name + '_' + self.name + '_tick'
        self.mode.player[self.tick_var] = 0

        self.running = self.config['start_running']
        self.start_value = self.config['start_value']
        self.restart_on_complete = self.config['restart_on_complete']
        self._ticks = 0
        self.end_value = self.config['end_value']
        self.ticks_remaining = 0
        self.max_value = self.config['max_value']
        self.direction = self.config['direction'].lower()
        self.tick_secs = self.config['tick_interval'] / 1000.0
        self.timer = None
        self.bcp = self.config['bcp']
        self.event_keys = set()
        self.delay = DelayManager(self.machine.delayRegistry)
        self.log = logging.getLogger('ModeTimer.' + name)
        self.debug = self.config['debug']

        if self.direction == 'down' and not self.end_value:
            self.end_value = 0  # need it to be 0 not None

        self.mode.player[self.tick_var] = self.start_value

        if self.debug:
            self.log.debug("----------- Initial Values -----------")
            self.log.debug("running: %s", self.running)
            self.log.debug("start_value: %s", self.start_value)
            self.log.debug("restart_on_complete: %s", self.restart_on_complete)
            self.log.debug("_ticks: %s", self._ticks)
            self.log.debug("end_value: %s", self.end_value)
            self.log.debug("ticks_remaining: %s", self.ticks_remaining)
            self.log.debug("max_value: %s", self.max_value)
            self.log.debug("direction: %s", self.direction)
            self.log.debug("tick_secs: %s", self.tick_secs)
            self.log.debug("--------------------------------------")

        if self.config['control_events']:
            self._setup_control_events(self.config['control_events'])

    def _setup_control_events(self, event_list):
        if self.debug:
            self.log.debug("Setting up control events")

        kwargs = None
        for entry in event_list:
            if entry['action'] == 'add':
                handler = self.add_time
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'subtract':
                handler = self.subtract_time
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'jump':
                handler = self.set_current_time
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'start':
                handler = self.start

            elif entry['action'] == 'stop':
                handler = self.stop

            elif entry['action'] == 'reset':
                handler = self.reset

            elif entry['action'] == 'restart':
                handler = self.restart

            elif entry['action'] == 'pause':
                handler = self.pause
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'set_tick_interval':
                handler = self.set_tick_interval
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'change_tick_interval':
                handler = self.change_tick_interval
                kwargs = {'change': entry['value']}
            else:
                raise AssertionError("Invalid control_event action {} in mode".
                                     format(entry['action']), self.name)

            if kwargs:
                self.event_keys.add(self.machine.events.add_handler(
                                    entry['event'], handler, **kwargs))
            else:
                self.event_keys.add(self.machine.events.add_handler(
                                    entry['event'], handler))

    def _remove_control_events(self):
        if self.debug:
            self.log.debug("Removing control events")

        for key in self.event_keys:
            self.machine.events.remove_handler_by_key(key)

    def reset(self, **kwargs):
        """Reset this timer based to the starting value that's already been configured.

        Does not start or stop the timer.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        if self.debug:
            self.log.debug("Resetting timer. New value: %s", self.start_value)

        self.set_current_time(self.start_value)

    def start(self, **kwargs):
        """Start this timer based on the starting value that's already been configured.

        Use set_current_time() if you want to set the starting time value.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        if self.debug:
            self.log.debug("Starting Timer.")

        if self._check_for_done():
            return()

        self.running = True

        self.delay.remove('pause')
        self._create_system_timer()

        self.machine.events.post('timer_' + self.name + '_started',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_started

        desc: The timer named (name) has just started.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='started',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

    def restart(self, **kwargs):
        """Restart the timer by resetting it and then starting it.

        Essentially this is just a reset() then a start().

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs
        self.reset()
        self.start()

    def stop(self, **kwargs):
        """Stop the timer and posts the 'timer_<name>_stopped' event.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        if self.debug:
            self.log.debug("Stopping Timer")

        self.delay.remove('pause')

        self.running = False
        self._remove_system_timer()

        self.machine.events.post('timer_' + self.name + '_stopped',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_stopped

        desc: The timer named (name) has stopped.

        This event is posted any time the timer stops, whether it stops because
        it ended or because it was stopped early by some other event.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='stopped',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

    def pause(self, timer_value=0, **kwargs):
        """Pause the timer and posts the 'timer_<name>_paused' event.

        Args:
            timer_value: How many seconds you want to pause the timer for. Note
                that this pause time is real-world seconds and does not take
                into consideration this timer's tick interval.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        if self.debug:
            self.log.debug("Pausing Timer for %s secs", timer_value)

        self.running = False

        pause_secs = timer_value

        self._remove_system_timer()
        self.machine.events.post('timer_' + self.name + '_paused',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_paused

        desc: The timer named (name) has paused.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''
        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='paused',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

        if pause_secs > 0:
            self.delay.add(name='pause', ms=pause_secs, callback=self.start)

    def timer_complete(self, **kwargs):
        """Automatically called when this timer completes.

        Posts the 'timer_<name>_complete' event. Can be manually called to mark this timer as complete.

        Args:
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        if self.debug:
            self.log.debug("Timer Complete")

        self.stop()

        if self.bcp:  # must be before the event post in case it stops the mode
            self.machine.bcp.send('timer', name=self.name, action='complete',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_remaining=self.ticks_remaining)

        self.machine.events.post('timer_' + self.name + '_complete',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_complete

        desc: The timer named (name) has completed.

        Note that this timer may reset and start again after this event is
        posted, depending on its settings.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''

        if self.restart_on_complete:

            if self.debug:
                self.log.debug("Restart on complete: True")

            self.reset()
            self.start()

    def _timer_tick(self, dt):
        # Automatically called by the core clock each tick
        del dt

        if self.debug:
            self.log.debug("Timer Tick")

        if not self.running:
            if self.debug:
                self.log.debug("Timer is not running. Will remove.")

            self._remove_system_timer()
            return

        if self.direction == 'down':
            self.mode.player[self.tick_var] -= 1
        else:
            self.mode.player[self.tick_var] += 1

        if not self._check_for_done():
            self.machine.events.post('timer_' + self.name + '_tick',
                                     ticks=self.mode.player[self.tick_var],
                                     ticks_remaining=self.ticks_remaining)
            '''event: timer_(name)_tick

            desc: The timer named (name) has just counted down (or up,
            depending on its settings).

            args:
                ticks: The new tick number this timer is at.
                ticks_remaining: The new number of ticks in this timer
                    remaining.
            '''

            if self.debug:
                self.log.debug("Ticks: %s, Remaining: %s",
                               self.mode.player[self.tick_var],
                               self.ticks_remaining)

            if self.bcp:
                self.machine.bcp.send('timer', name=self.name, action='tick',
                                      ticks=self.mode.player[self.tick_var],
                                      ticks_remaining=self.ticks_remaining)

    def add_time(self, timer_value, **kwargs):
        """Add ticks to this timer.

        Args:
            timer_value: The number of ticks you want to add to this timer's
                current value.
            kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        ticks_added = timer_value

        new_value = self.mode.player[self.tick_var] + ticks_added

        if self.max_value and new_value > self.max_value:
            new_value = self.max_value

        self.mode.player[self.tick_var] = new_value
        ticks_added = new_value - timer_value

        self.machine.events.post('timer_' + self.name + '_time_added',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_added=ticks_added,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_time_added

        desc: The timer named (name) has just had time added to it.

        args:
            ticks: The new tick number this timer is at.
            ticks_remaining: The new number of ticks in this timer remaining.
            ticks_added: How many ticks were just added.
        '''

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name, action='time_added',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_added=ticks_added,
                                  ticks_remaining=self.ticks_remaining)

        self._check_for_done()

    def subtract_time(self, timer_value, **kwargs):
        """Subtract ticks from this timer.

        Args:
            timer_value: The number of ticks you want to subtract from this
                timer's current value.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        ticks_subtracted = timer_value

        self.mode.player[self.tick_var] -= ticks_subtracted

        self.machine.events.post('timer_' + self.name + '_time_subtracted',
                                 ticks=self.mode.player[self.tick_var],
                                 ticks_subtracted=ticks_subtracted,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_time_subtracted

        desc: The timer named (name) just had some ticks removed.

        args:
            ticks: The new current tick number this timer is at.
            ticks_remaining: The new number of ticks in this timer remaining.
            time_subtracted: How many ticks were just subtracted from this
                timer. (This number will be positive, indicating the ticks
                subtracted.)
        '''

        if self.bcp:
            self.machine.bcp.send('timer', name=self.name,
                                  action='time_subtracted',
                                  ticks=self.mode.player[self.tick_var],
                                  ticks_subtracted=ticks_subtracted,
                                  ticks_remaining=self.ticks_remaining)

        self._check_for_done()

    def _check_for_done(self):
        # Checks to see if this timer is done. Automatically called anytime the
        # timer's value changes.

        if self.debug:
            self.log.debug("Checking to see if timer is done. Ticks: %s, End "
                           "Value: %s, Direction: %s",
                           self.mode.player[self.tick_var], self.end_value,
                           self.direction)

        if (self.direction == 'up' and self.end_value is not None and
                self.mode.player[self.tick_var] >= self.end_value):
            self.timer_complete()
            return True
        elif (self.direction == 'down' and
                self.mode.player[self.tick_var] <= self.end_value):
            self.timer_complete()
            return True

        if self.end_value is not None:
            self.ticks_remaining = abs(self.end_value -
                                       self.mode.player[self.tick_var])

        if self.debug:
            self.log.debug("Timer is not done")

        return False

    def _create_system_timer(self):
        # Creates the clock event which drives this mode timer's tick method.
        self._remove_system_timer()
        self.timer = self.machine.clock.schedule_interval(self._timer_tick, self.tick_secs)

    def _remove_system_timer(self):
        # Removes the clock event associated with this mode timer.
        if self.timer:
            self.machine.clock.unschedule(self.timer)
            self.timer = None

    def change_tick_interval(self, change=0.0, **kwargs):
        """Change the interval for each "tick" of this timer.

        Args:
            change: Float or int of the change you want to make to this timer's
                tick rate. Note this value is added to the current tick
                interval. To set an absolute value, use the set_tick_interval()
                method. To shorten the tick rate, use a negative value.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.tick_secs *= change
        self._create_system_timer()

    def set_tick_interval(self, timer_value, **kwargs):
        """Set the number of seconds between ticks for this timer.

        This is an absolute setting. To apply a change to the current value, use the change_tick_interval() method.

        Args:
            timer_value: The new number of seconds between each tick of this
                timer. This value should always be positive.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.tick_secs = abs(timer_value)
        self._create_system_timer()

    def set_current_time(self, timer_value, **kwargs):
        """Set the current amount of time of this timer.

        This value is expressed in "ticks" since the interval per tick can be something other than 1 second).

        Args:
            timer_value: Integer of the current value you want this timer to be.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.mode.player[self.tick_var] = int(timer_value)

        if self.max_value and self.mode.player[self.tick_var] > self.max_value:
            self.mode.player[self.tick_var] = self.max_value

    def kill(self):
        """Stop this timer and also removes all the control events."""
        self.stop()
        self._remove_control_events()
