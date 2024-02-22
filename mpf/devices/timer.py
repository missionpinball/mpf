"""Mode timers."""
from typing import List, Optional

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.delays import DelayManager
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.mode import Mode

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.clock import PeriodicTask     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.events import EventHandlerKey     # pylint: disable-msg=cyclic-import,unused-import


# pylint: disable-msg=too-many-instance-attributes
@DeviceMonitor("running", "ticks", "end_value", "max_value", "start_value")
class Timer(ModeDevice):

    """Parent class for a mode timer.

    Args:
    ----
        machine: The main MPF MachineController object.
        name: The string name of this timer.
    """

    config_section = 'timers'
    collection = 'timers'
    class_label = 'timer'

    def __init__(self, machine: "MachineController", name: str) -> None:
        """initialize mode timer."""
        super().__init__(machine, name)
        self.machine = machine
        self.name = name

        self.running = False
        self.start_value = None             # type: Optional[int]
        self.restart_on_complete = None     # type: Optional[bool]
        self._ticks = 0
        self.tick_var = None                # type: Optional[str]
        self.tick_secs = None               # type: Optional[float]
        self.player = None                  # type: Optional[Player]
        self.end_value = None               # type: Optional[int]
        self.max_value = None               # type: Optional[int]
        self.ticks_remaining = None         # type: Optional[int]
        self.direction = None               # type: Optional[str]
        self.timer = None                   # type: Optional[PeriodicTask]
        self.event_keys = list()            # type: List[EventHandlerKey]
        self.delay = None                   # type: Optional[DelayManager]

    async def device_added_to_mode(self, mode: Mode) -> None:
        """Device added in mode."""
        await super().device_added_to_mode(mode)
        self.tick_var = '{}_{}_tick'.format(mode.name, self.name)

    async def _initialize(self):
        await super()._initialize()
        self.ticks_remaining = 0
        self.max_value = self.config['max_value']
        self.direction = self.config['direction']
        self.tick_secs = None
        self.timer = None
        self.event_keys = list()
        self.delay = DelayManager(self.machine)

        self.restart_on_complete = self.config['restart_on_complete']
        self.end_value = None
        self.start_value = None
        self.ticks = None

        if self.config['debug']:
            self.configure_logging('Timer.' + self.name,
                                   'full', 'full')
        else:
            self.configure_logging('Timer.' + self.name,
                                   self.config['console_log'],
                                   self.config['file_log'])

        self.debug_log("----------- Initial Values -----------")
        self.debug_log("running: %s", self.running)
        self.debug_log("start_value: %s", self.start_value)
        self.debug_log("restart_on_complete: %s", self.restart_on_complete)
        self.debug_log("_ticks: %s", self.ticks)
        self.debug_log("end_value: %s", self.end_value)
        self.debug_log("ticks_remaining: %s", self.ticks_remaining)
        self.debug_log("max_value: %s", self.max_value)
        self.debug_log("direction: %s", self.direction)
        self.debug_log("tick_secs: %s", self.tick_secs)
        self.debug_log("--------------------------------------")

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Set up control events when mode is loaded."""
        del mode
        self.player = player
        self.tick_secs = self.config['tick_interval'].evaluate([])

        try:
            self.end_value = self.config['end_value'].evaluate([])
        except AttributeError:
            self.end_value = None

        if self.direction == 'down' and not self.end_value:
            self.end_value = 0  # need it to be 0 not None

        self.start_value = self.config['start_value'].evaluate([])
        self.ticks = self.start_value

        if self.config['control_events']:
            self._setup_control_events(self.config['control_events'])

        if self.config['start_running']:
            self.start()

    @property
    def ticks(self):
        """Return ticks."""
        return self._ticks

    @ticks.setter
    def ticks(self, value):
        self._ticks = value

        try:
            self.player[self.tick_var] = value
            '''player_var: (mode)_(timer)_tick

            desc: Stores the current tick value for the timer from the mode
            (mode) with the time name (timer). For example, a timer called
            "my_timer" which is in the config for "mode1" will store its tick
            value in the player variable ``mode1_my_timer_tick``.
            '''

        except TypeError:
            pass

    @property
    def can_exist_outside_of_game(self):
        """Timer can live outside of games."""
        return True

    def _setup_control_events(self, event_list):
        self.debug_log("Setting up control events")

        kwargs = {}
        for entry in event_list:
            if entry['action'] in ('add', 'subtract', 'jump', 'pause', 'set_tick_interval'):
                handler = getattr(self, entry['action'])
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] in ('start', 'stop', 'reset', 'restart'):
                handler = getattr(self, entry['action'])

            elif entry['action'] == 'change_tick_interval':
                handler = self.change_tick_interval
                kwargs = {'change': entry['value']}

            elif entry['action'] == 'set_tick_interval':
                handler = self.set_tick_interval
                kwargs = {'timer_value': entry['value']}

            elif entry['action'] == 'reset_tick_interval':
                handler = self.set_tick_interval
                kwargs = {'timer_value': self.config['tick_interval']}

            else:
                raise AssertionError("Invalid control_event action {} in mode".
                                     format(entry['action']), self.name)

            self.event_keys.append(
                self.machine.events.add_handler(entry['event'], handler, **kwargs))

    def _remove_control_events(self):
        self.debug_log("Removing control events")

        for key in self.event_keys:
            self.machine.events.remove_handler_by_key(key)

    def reset(self, **kwargs):
        """Reset this timer based to the starting value that's already been configured.

        Does not start or stop the timer.

        Args:
        ----
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.debug_log("Resetting timer. New value: %s", self.start_value)

        self.jump(self.start_value)

    def start(self, **kwargs):
        """Start this timer based on the starting value that's already been configured.

        Use jump() if you want to set the starting time value.

        Args:
        ----
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        # do not start if timer is already running
        if self.running:
            return

        self.info_log("Starting Timer.")

        if self._check_for_done():
            return

        self.running = True

        self.delay.remove('pause')
        self._create_system_timer()

        self.machine.events.post('timer_' + self.name + '_started',
                                 ticks=self.ticks,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_started

        desc: The timer named (name) has just started.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''

        self._post_tick_events()
        # since lots of slides and stuff are tied to the timer tick, we want
        # to post an initial tick event also that represents the starting
        # timer value.

    def restart(self, **kwargs):
        """Restart the timer by resetting it and then starting it.

        Essentially this is just a reset() then a start().

        Args:
        ----
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs
        self.reset()
        # If the timer is not running, start it
        if not self.running:
            self.start()
        # If the timer is running, post an updated tick event
        else:
            self._post_tick_events()

    def stop(self, **kwargs):
        """Stop the timer and posts the 'timer_<name>_stopped' event.

        Args:
        ----
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.info_log("Stopping Timer")

        self.delay.remove('pause')

        self.running = False
        self._remove_system_timer()

        self.machine.events.post('timer_' + self.name + '_stopped',
                                 ticks=self.ticks,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_stopped

        desc: The timer named (name) has stopped.

        This event is posted any time the timer stops, whether it stops because
        it ended or because it was stopped early by some other event.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''

    def pause(self, timer_value=0, **kwargs):
        """Pause the timer and posts the 'timer_<name>_paused' event.

        Args:
        ----
            timer_value: How many seconds you want to pause the timer for. Note
                that this pause time is real-world seconds and does not take
                into consideration this timer's tick interval.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        if not timer_value:
            pause_ms = 0  # make sure it's not None, etc.
        else:
            pause_ms = self._get_timer_value(timer_value) * 1000  # delays happen in ms

        self.info_log("Pausing Timer for %s ms", pause_ms)

        self.running = False

        self._remove_system_timer()
        self.machine.events.post('timer_' + self.name + '_paused',
                                 ticks=self.ticks,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_paused

        desc: The timer named (name) has paused.

        args:
            ticks: The current tick number this timer is at.
            ticks_remaining: The number of ticks in this timer remaining.
        '''

        if pause_ms > 0:
            self.delay.add(name='pause', ms=pause_ms, callback=self.start)

    def timer_complete(self, **kwargs):
        """Automatically called when this timer completes.

        Posts the 'timer_<name>_complete' event. Can be manually called to mark
        this timer as complete.

        Args:
        ----
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.info_log("Timer Complete")

        self.stop()

        self.machine.events.post('timer_' + self.name + '_complete',
                                 ticks=self.ticks,
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

            self.debug_log("Restart on complete: True")

            self.restart()

    def _timer_tick(self):
        # Automatically called by the core clock each tick
        if self._debug:
            self.debug_log("Timer Tick")

        if not self.running:
            if self._debug:
                self.debug_log("Timer is not running. Will remove.")

            self._remove_system_timer()
            return

        if self.direction == 'down':
            self.ticks -= 1
        else:
            self.ticks += 1

        self._post_tick_events()

    def _post_tick_events(self):
        if not self._check_for_done():
            self.machine.events.post('timer_{}_tick'.format(self.name),
                                     ticks=self.ticks,
                                     ticks_remaining=self.ticks_remaining)
            '''event: timer_(name)_tick

            desc: The timer named (name) has just counted down (or up,
            depending on its settings).

            args:
                ticks: The new tick number this timer is at.
                ticks_remaining: The new number of ticks in this timer
                    remaining.
            '''

            if self._debug:
                self.debug_log("Ticks: %s, Remaining: %s",
                               self.ticks,
                               self.ticks_remaining)

    def add(self, timer_value, **kwargs):
        """Add ticks to this timer.

        Args:
        ----
            timer_value: The number of ticks you want to add to this timer's
                current value.
            kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        timer_value = self._get_timer_value(timer_value)
        ticks_added = timer_value

        new_value = self.ticks + ticks_added

        if self.max_value and new_value > self.max_value:
            new_value = self.max_value

        self.ticks = new_value
        ticks_added = new_value - timer_value

        self.machine.events.post('timer_' + self.name + '_time_added',
                                 ticks=self.ticks,
                                 ticks_added=ticks_added,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_time_added

        desc: The timer named (name) has just had time added to it.

        args:
            ticks: The new tick number this timer is at.
            ticks_remaining: The new number of ticks in this timer remaining.
            ticks_added: How many ticks were just added.
        '''

        self._check_for_done()

    def subtract(self, timer_value, **kwargs):
        """Subtract ticks from this timer.

        Args:
        ----
            timer_value: The number of ticks you want to subtract from this
                timer's current value.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        ticks_subtracted = self._get_timer_value(timer_value)

        self.ticks -= ticks_subtracted

        self.machine.events.post('timer_' + self.name + '_time_subtracted',
                                 ticks=self.ticks,
                                 ticks_subtracted=ticks_subtracted,
                                 ticks_remaining=self.ticks_remaining)
        '''event: timer_(name)_time_subtracted

        desc: The timer named (name) just had some ticks removed.

        args:
            ticks: The new current tick number this timer is at.
            ticks_remaining: The new number of ticks in this timer remaining.
            ticks_subtracted: How many ticks were just subtracted from this
                timer. (This number will be positive, indicating the ticks
                subtracted.)
        '''

        self._check_for_done()

    def _check_for_done(self):
        # Checks to see if this timer is done. Automatically called anytime the
        # timer's value changes.
        if self._debug:
            self.debug_log("Checking to see if timer is done. Ticks: %s, End "
                           "Value: %s, Direction: %s",
                           self.ticks, self.end_value,
                           self.direction)

        if (self.direction == 'up' and self.end_value is not None and
                self.ticks >= self.end_value):
            self.timer_complete()
            return True

        if (self.direction == 'down' and
                self.ticks <= self.end_value):
            self.timer_complete()
            return True

        if self.end_value is not None:
            self.ticks_remaining = abs(self.end_value -
                                       self.ticks)

        if self._debug:
            self.debug_log("Timer is not done")

        return False

    def _create_system_timer(self):
        # Creates the clock event which drives this mode timer's tick method.
        self._remove_system_timer()
        self.timer = self.machine.clock.schedule_interval(self._timer_tick,
                                                          self.tick_secs)

    def _remove_system_timer(self):
        # Removes the clock event associated with this mode timer.
        if self.timer:
            self.machine.clock.unschedule(self.timer)
            self.timer = None

    @staticmethod
    def _get_timer_value(timer_value):
        if hasattr(timer_value, "evaluate"):
            # Convert to int for ticks; config_spec must be float for change_tick_interval
            return int(timer_value.evaluate([]))
        return timer_value

    def change_tick_interval(self, change=0.0, **kwargs):
        """Change the interval for each "tick" of this timer.

        Args:
        ----
            change: Float or int of the change you want to make to this timer's
                tick rate. Note this value is multiplied by the current tick
                interval: >1 will increase the tick interval (slow the timer) and
                <1 will decrease the tick interval (accelerate the timer).
                To set an absolute value, use the set_tick_interval() method.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.tick_secs *= change.evaluate([])
        self._create_system_timer()

    def set_tick_interval(self, timer_value, **kwargs):
        """Set the number of seconds between ticks for this timer.

        This is an absolute setting. To apply a change to the current value,
        use the change_tick_interval() method.

        Args:
        ----
            timer_value: The new number of seconds between each tick of this
                timer. This value should always be positive.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        self.tick_secs = abs(self._get_timer_value(timer_value.evaluate(kwargs)))
        self._create_system_timer()

    def jump(self, timer_value, **kwargs):
        """Set the current amount of time of this timer.

        This value is expressed in "ticks" since the interval per tick can be
        something other than 1 second).

        Args:
        ----
            timer_value: Integer of the current value you want this timer to be.
            **kwargs: Not used in this method. Only exists since this method is
                often registered as an event handler which may contain
                additional keyword arguments.
        """
        del kwargs

        self.ticks = self._get_timer_value(timer_value)

        if self.max_value and self.ticks > self.max_value:
            self.ticks = self.max_value

        self._remove_system_timer()
        self._create_system_timer()

        self._check_for_done()

    def device_removed_from_mode(self, mode: Mode):
        """Stop this timer and also removes all the control events."""
        self.stop()
        self._remove_control_events()
