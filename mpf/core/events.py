"""Classes for the EventManager and QueuedEvents."""
import inspect
from collections import deque, namedtuple, defaultdict
import uuid

import asyncio
from functools import partial, lru_cache
from unittest.mock import MagicMock

from typing import Dict, Any, Tuple, Optional, Callable, List

from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController      # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.placeholder_manager import BaseTemplate   # pylint: disable-msg=cyclic-import,unused-import
    from typing import Deque    # pylint: disable-msg=cyclic-import,unused-import

EventHandlerKey = namedtuple("EventHandlerKey", ["key", "event"])
RegisteredHandler = namedtuple("RegisteredHandler", ["callback", "priority", "kwargs", "key", "condition",
                                                     "blocking_facility"])
PostedEvent = namedtuple("PostedEvent", ["event", "type", "callback", "kwargs"])


class EventHandlerException(Exception):

    """Exception from within an event handler."""


class EventManager(MpfController):

    """Handles all the events and manages the handlers in MPF."""

    config_name = "event_manager"

    __slots__ = ["registered_handlers", "event_queue", "callback_queue", "monitor_events", "_queue_tasks", "_stopped"]

    def __init__(self, machine: "MachineController") -> None:
        """Initialize EventManager."""
        super().__init__(machine)

        self.registered_handlers = defaultdict(list)    # type: Dict[str, List[RegisteredHandler]]
        self.event_queue = deque([])        # type: Deque[PostedEvent]
        self.callback_queue = deque([])     # type: Deque[Tuple[Any, dict]]
        self.monitor_events = False
        self._queue_tasks = []              # type: List[asyncio.Task]
        self._stopped = False

        self.add_handler("debug_dump_stats", self._debug_dump_events)

    def _debug_dump_events(self, **kwargs):
        del kwargs
        self.log.info("--- DEBUG DUMP EVENTS ---")
        self.log.info("Total registered_handlers: %s. Total event_queue: %s. Total callback_queue: %s. "
                      "Total _queue_tasks: %s", len(self.registered_handlers), len(self.event_queue),
                      len(self.callback_queue), len(self._queue_tasks))
        self.log.info("Registered Handlers:")
        handlers = sorted(self.registered_handlers.items(), key=lambda x: -len(x[1]))
        for event_name, event_list in handlers:
            self.log.info("  Total handlers: %s (for %s)", len(event_list), event_name)

        self.log.info("Queue events:")
        for event_task in self._queue_tasks:
            self.log.info(" %s:", event_task)

        self.log.info("--- DEBUG DUMP EVENTS END ---")

    @lru_cache()
    def get_event_and_condition_from_string(self, event_string: str) -> Tuple[str, Optional["BaseTemplate"], int]:
        """Parse an event string to divide the event name from a possible placeholder / conditional in braces.

        Args:
        ----
            event_string: String to parse

        Returns 2-item tuple- First item is the event name. Second item is the
        condition (A BoolTemplate instance) if it exists, or None if it doesn't.
        """
        placeholder = None
        additional_priority = 0
        if event_string[-1:] == "}":
            first_bracket_pos = event_string.find("{")
            if first_bracket_pos < 0:
                raise ValueError('Failed to parse condition in event name, '
                                 'please remedy "{}"'.format(event_string))
            if " " in event_string[0:first_bracket_pos]:
                raise ValueError('Cannot handle events with spaces in the event name, '
                                 'please remedy "{}"'.format(event_string))
            placeholder = self.machine.placeholder_manager.build_bool_template(event_string[first_bracket_pos + 1:-1])
            event_string = event_string[0:first_bracket_pos]
        else:
            if " " in event_string:
                raise ValueError('Cannot handle events with spaces in the event name, '
                                 'please remedy "{}"'.format(event_string))
            if "{" in event_string:
                raise ValueError('Failed to parse condition in event name, '
                                 'please remedy "{}"'.format(event_string))

        priority_start = event_string.find(".")
        if priority_start > 0:
            try:
                additional_priority = int(event_string[priority_start + 1:])
            except ValueError:
                raise ValueError('Failed to parse priority in event name, '
                                 f'please remedy "{event_string}". Does your '
                                 'event name contain a dot?')

            event_string = event_string[:priority_start]

        return event_string, placeholder, additional_priority

    def add_async_handler(self, event: str, handler: Any, priority: int = 1, blocking_facility: Any = None,
                          **kwargs) -> EventHandlerKey:
        """Register a coroutine as event handler."""
        return self.add_handler(event, partial(self._async_handler_coroutine, handler), priority, blocking_facility,
                                **kwargs)

    def _async_handler_coroutine(self, _coroutine, queue, **kwargs):
        queue.wait()
        task = asyncio.create_task(_coroutine(**kwargs))
        task.add_done_callback(partial(self._async_handler_done, queue))

    @staticmethod
    def _async_handler_done(queue, future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass
        queue.clear()

    def add_handler(self, event: str, handler: Any, priority: int = 1, blocking_facility: Any = None,
                    **kwargs) -> EventHandlerKey:
        """Register an event handler to respond to an event.

        Args:
        ----
            event: String name of the event you're adding a handler for. Since
                events are text strings, they don't have to be pre-defined.
            handler: The callable method that will be called when the event is
                fired. Since it's possible for events to have kwargs attached
                to them, the handler method must include ``**kwargs`` in its
                signature.
            priority: An arbitrary integer value that defines what order the
                handlers will be called in. The default is 1, so if you have a
                handler that you want to be called first, add it here with a
                priority of 2. (Or 3 or 10 or 100000.) The numbers don't matter.
                They're called from highest to lowest. (i.e. priority 100 is
                called before priority 1.)
            blocking_facility: Facility which can block this event.
            **kwargs: Any any additional keyword/argument pairs entered here
                will be attached to the handler and called whenever that
                handler is called. Note these are in addition to kwargs that
                could be passed as part of the event post. If there's a
                conflict, the event-level ones will win.

        Returns EventHandlerKey to the handler which you can use to later remove
        the handler via ``remove_handler_by_key``.

        For example:

        .. code::

            my_handler = self.machine.events.add_handler('ev', self.test))

        Then later to remove all the handlers that a module added, you could:
        for handler in handler_list:
        ``events.remove_handler(my_handler)``
        
        
        A fully working example to get some initial working code might look like explained below. In your modes config file have the section

        .. code::
        
            mode:
                start_events: ball_started
                priority: 100
                code: base.My_Base  #base is the name of my code file (base.py), My_Base is the name of the class to be used from that source file

        Here the mode being used is my base mode, of course it could be done for any mode. Some basic code to read and write some player variable might look like below.

        .. code::
        
            from mpf.core.mode import Mode
            from mpf.core.events import event_handler

            class My_Base(Mode): #base mode

                def my_event_handler(self, *args, **kwargs):
                    print("My event handler is starting")
        
                    player = self.machine.game.player    
                    if not player:
                        return    # do something reasonable here but do not crash in the next line

                    # read player variable
                    print(player["status_target_light_red_0"]) #the variable status_target_light_red_0 is defined in the player_vars section of the config.yaml file
   
                    #with every fired event alternate variable value between 0 and 1
                    
                    if(player["status_target_light_red_0"] == 0):
                        player["status_target_light_red_0"] = 1 #set the variable to a value
                    else:
                        player["status_target_light_red_0"] = 0
    
                def mode_start(self, **kwargs):
                    print("My custom mode code is starting")
                    my_handler = self.machine.events.add_handler('toggle_light', self.my_event_handler)
        
        """
        if event is None:
            raise AssertionError("Cannot pass event None.")
        if not self.machine.options['production']:
            if hasattr(self.machine, "switches") and event in self.machine.switches:
                self.raise_config_error('Switch name "{name}" name used as event handler for {handler}. '
                                        'Did you mean "{name}_active"?'.format(name=event, handler=handler), 1)
            if not callable(handler):
                raise AssertionError('Cannot add handler "{}" for event "{}". Did you '
                                     'accidentally add parenthesis to the end of the '
                                     'handler you passed?'.format(handler, event))

            sig = inspect.signature(handler)
            if 'kwargs' not in sig.parameters:
                raise AssertionError("Handler {} for event '{}' is missing **kwargs. Actual signature: {}".format(
                    handler, event, sig))

            if sig.parameters['kwargs'].kind != inspect.Parameter.VAR_KEYWORD:
                raise AssertionError("Handler {} for event '{}' param kwargs is missing '**'. "
                                     "Actual signature: {}".format(handler, event, sig))

        event, condition, additional_priority = self.get_event_and_condition_from_string(event)
        priority += additional_priority

        key = uuid.uuid4()

        # An event 'handler' in our case is a tuple with 4 elements:
        # the handler method, priority, dict of kwargs, & uuid key
        if hasattr(handler, "relative_priority") and not isinstance(handler, MagicMock):
            priority += handler.relative_priority

        self.registered_handlers[event].append(RegisteredHandler(handler, priority, kwargs, key, condition,
                                                                 blocking_facility))

        if self._debug:
            self.debug_log("Registered %s as a handler for '%s', priority: %s, "
                           "kwargs: %s",
                           self._pretty_format_handler(handler), event, priority, kwargs)

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        if len(self.registered_handlers[event]) > 1:
            self.registered_handlers[event].sort(key=lambda x: x.priority, reverse=True)

        if self._info:
            self._verify_handlers(event, self.registered_handlers[event])

        return EventHandlerKey(key, event)

    def _get_handler_signature(self, handler):
        """Perform black magic to calculate a signature for a handler."""
        cls = handler.callback.__self__

        # noinspection PyProtectedMember
        # pylint: disable-msg=protected-access
        if hasattr(self.machine, "device_manager") and cls == self.machine.device_manager and \
                handler.callback == self.machine.device_manager._control_event_handler:
            cls = (handler.kwargs["callback"].__self__, handler.kwargs["ms_delay"])

        handler_signature = (cls, handler.priority, handler.condition)
        return handler_signature

    def _verify_handlers(self, event, sorted_handlers):
        """Verify that no races can happen."""
        if not sorted_handlers or len(sorted_handlers) <= 1 or event.startswith("init_phase_"):
            return

        seen = set()
        collisions = []
        for handler in sorted_handlers:
            if not inspect.ismethod(handler.callback):
                continue

            handler_signature = self._get_handler_signature(handler)

            if handler_signature not in seen:
                seen.add(handler_signature)

            else:
                collisions.append(handler_signature)

        for collision in collisions:
            handlers = [x for x in sorted_handlers if inspect.ismethod(x.callback) and
                        self._get_handler_signature(x) == collision]
            self.info_log(
                "Unordered handler for class {} on event {} with priority {}. Handlers: {}. The order of those "
                "handlers is not defined and they will be executed in random order. This might lead to race "
                "conditions and potential bugs.".format(collision[0], event, collision[1], handlers)
            )

    def replace_handler(self, event: str, handler: Any, priority: int = 1,
                        **kwargs: dict) -> EventHandlerKey:
        """Check to see if a handler (optionally with kwargs) is registered for an event and replaces it if so.

        Args:
        ----
            event: The event you want to check to see if this handler is
                registered for.
            handler: The method of the handler you want to check.
            priority: Optional priority of the new handler that will be
                registered.
            **kwargs: The kwargs you want to check and the kwargs that will be
                registered with the new handler.

        If you don't pass kwargs, this method will just look for the handler and
        event combination. If you do pass kwargs, it will make sure they match
        before replacing the existing entry.

        If this method doesn't find a match, it will still add the new handler.
        """
        # Check to see if this handler is already registered for this event.
        # If we don't have kwargs, then we'll look for just the handler meth.
        # If we have kwargs, we'll look for that combination. If it finds it,
        # remove it.
        if event in self.registered_handlers:
            if kwargs:
                # slice the full list [:] to make a copy so we can delete from the
                # original while iterating
                for rh in self.registered_handlers[event][:]:
                    if rh[0] == handler and rh[2] == kwargs:
                        self.registered_handlers[event].remove(rh)
            else:
                for rh in self.registered_handlers[event][:]:
                    if rh[0] == handler:
                        self.registered_handlers[event].remove(rh)

        return self.add_handler(event, handler, priority, **kwargs)

    def remove_all_handlers_for_event(self, event: str) -> None:
        """Remove all handlers for event.

        Use carefully. This is currently used to remove handlers for all init events which only occur once.
        """
        if event in self.registered_handlers:
            del self.registered_handlers[event]

    @staticmethod
    def _pretty_format_handler(handler):
        """Pretty format handler."""
        parts = str(handler).split(' ')
        return parts[2] if len(parts) >= 3 else parts[0]

    def _pretty_log_removed_handler(self, handler, event):
        """Pretty log removed handler."""
        self.debug_log("Removing method %s from event %s", self._pretty_format_handler(handler), event)

    def remove_handler(self, method: Any) -> None:
        """Remove an event handler from all events a method is registered to handle.

        Args:
        ----
            method : The method whose handlers you want to remove.
        """
        events_to_delete_if_empty = []
        for event, handler_list in self.registered_handlers.items():
            for handler_tup in handler_list[:]:  # copy via slice
                if handler_tup[0] == method:
                    handler_list.remove(handler_tup)
                    if self._debug:
                        self._pretty_log_removed_handler(method, event)
                    events_to_delete_if_empty.append(event)

        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handler_by_event(self, event: str, handler: Any) -> None:
        """Remove the handler you pass from the event you pass.

        Args:
        ----
            event: The name of the event you want to remove the handler from.
            handler: The handler method you want to remove.

        Note that keyword arguments for the handler are not taken into
        consideration. In other words, this method only removes the registered
        handler / event combination, regardless of whether the keyword
        arguments match or not.
        """
        events_to_delete_if_empty = []
        if event in self.registered_handlers:
            for handler_tup in self.registered_handlers[event][:]:
                if handler_tup[0] == handler:
                    self.registered_handlers[event].remove(handler_tup)
                    if self._debug:
                        self._pretty_log_removed_handler(handler, event)
                    events_to_delete_if_empty.append(event)

        for this_event in events_to_delete_if_empty:
            self._remove_event_if_empty(this_event)

    def remove_handler_by_key(self, key: EventHandlerKey) -> None:
        """Remove a registered event handler by key.

        Args:
        ----
            key: The key of the handler you want to remove
        """
        if key.event not in self.registered_handlers:
            return
        events_to_delete_if_empty = []
        for handler_tup in self.registered_handlers[key.event][:]:  # copy via slice
            if handler_tup.key == key.key:
                self.registered_handlers[key.event].remove(handler_tup)
                if self._debug:
                    self._pretty_log_removed_handler(handler_tup[0], key.event)
                events_to_delete_if_empty.append(key.event)
        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handlers_by_keys(self, key_list: List[EventHandlerKey]) -> None:
        """Remove multiple event handlers based on a passed list of keys.

        Args:
        ----
            key_list: A list of keys of the handlers you want to remove
        """
        for key in key_list:
            self.remove_handler_by_key(key)

    def _remove_event_if_empty(self, event: str) -> None:
        # Checks to see if the event doesn't have any more registered handlers,
        # removes it if so.

        if event not in self.registered_handlers:
            return

        if not self.registered_handlers[event]:  # if value is empty list
            del self.registered_handlers[event]
            if self._debug:
                self.debug_log("Removing event %s since there are no more"
                               " handlers registered for it", event)

    def wait_for_event(self, event_name: str) -> asyncio.Future:
        """Wait for event."""
        return self.wait_for_any_event([event_name])

    def wait_for_any_event(self, event_names: List[str]) -> asyncio.Future:
        """Wait for any event from event_names."""
        future = asyncio.Future()   # type: asyncio.Future
        keys = []   # type: List[EventHandlerKey]
        for event_name in event_names:
            keys.append(self.add_handler(event_name, partial(self._wait_handler,
                                                             _future=future,
                                                             _keys=keys,
                                                             event=event_name)))
        return future

    def _wait_handler(self, _future: asyncio.Future, _keys: List[EventHandlerKey], **kwargs):
        for key in _keys:
            self.remove_handler_by_key(key)

        if _future.cancelled():
            return
        _future.set_result(kwargs)

    def does_event_exist(self, event_name: str) -> bool:
        """Check to see if any handlers are registered for the event name that is passed.

        Args:
        ----
            event_name : The string name of the event you want to check.

        Returns True or False.
        """
        return event_name in self.registered_handlers

    @staticmethod
    def _set_result(_future, **kwargs):
        if not _future.done():
            _future.set_result(kwargs)

    def post_async(self, event: str, **kwargs: dict) -> asyncio.Future:
        """Post event and wait until all handlers are done."""
        future = asyncio.Future()   # type: asyncio.Future
        self.post(event, partial(self._set_result, _future=future), **kwargs)
        return future

    def post_relay_async(self, event: str, **kwargs: dict) -> asyncio.Future:
        """Post relay event, wait until all handlers are done and return result."""
        future = asyncio.Future()   # type: asyncio.Future
        self.post_relay(event, partial(self._set_result, _future=future), **kwargs)
        return future

    def post_queue_async(self, event: str, **kwargs: dict) -> asyncio.Future:
        """Post queue event, wait until all handlers are done and locks are released."""
        future = asyncio.Future()   # type: asyncio.Future
        self.post_queue(event, partial(self._set_result, _future=future), **kwargs)
        return future

    def post(self, event: str, callback=None, **kwargs) -> None:
        """Post an event which causes all the registered handlers to be called.

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registered. (Higher
        priority values will be processed first.)

        Args:
        ----
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            callback: An optional method which will be called when the final
                handler is done processing this event. Default is None.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (The event manager will enforce that
                handlers have ``**kwargs`` in their signatures when they're
                registered to prevent run-time crashes from unexpected kwargs
                that were included in ``post()`` calls.
        """
        self._post(event, None, callback, **kwargs)

    def post_boolean(self, event: str, callback=None, **kwargs) -> None:
        """Post an boolean event which causes all the registered handlers to be called one-by-one.

        Boolean events differ from regular events in that if any handler
        returns False, the remaining handlers will not be called.

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registered. (Higher
        priority values will be processed first.)

        Args:
        ----
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            callback: An optional method which will be called when the final
                handler is done processing this event. Default is None. If
                any handler returns False and cancels this boolean event, the
                callback will still be called, but a new kwarg ev_result=False
                will be passed to it.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler.
        """
        self._post(event, 'boolean', callback, **kwargs)

    def post_queue(self, event, callback, **kwargs):
        """Post a queue event which causes all the registered handlers to be called.

        Queue events differ from standard events in that individual handlers
        are given the option to register a "wait", and the callback will not be
        called until any handler(s) that registered a wait will have to release
        that wait. Once all the handlers release their waits, the callback is
        called.

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registered. (Higher
        numeric values will be processed first.)

        Args:
        ----
        ----
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            callback: The method which will be called when the final
                handler is done processing this event and any handlers that
                registered waits have cleared their waits.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add ``**kwargs`` to your handler
                methods if certain ones don't need them.)

        Example:
        -------
        Post the queue event called *pizza_time*, and then call
        ``self.pizza_done`` when done:

        .. code::

             self.machine.events.post_queue('pizza_time', self.pizza_done)

        """
        self._post(event, 'queue', callback, **kwargs)

    def post_relay(self, event: str, callback=None, **kwargs) -> None:
        """Post a relay event which causes all the registered handlers to be called.

        A dictionary can be passed from handler-to-handler and modified
        as needed.

        Args:
        ----
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            callback: The method which will be called when the final handler is
                done processing this event. Default is None.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add ``**kwargs`` to your handler
                methods if certain ones don't need them.)

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registered. (Higher
        priority values will be processed first.)

        Relay events differ from standard events in that the resulting kwargs
        from one handler are passed to the next handler. (In other words,
        standard events mean that all the handlers get the same initial kwargs,
        whereas relay events "relay" the resulting kwargs from one handler to
        the next.)
        """
        self._post(event, 'relay', callback, **kwargs)

    def _post(self, event: str, ev_type: Optional[str], callback, **kwargs: dict) -> None:
        if self._stopped:
            self.warning_log("Event after stop: ===='%s'==== Type: %s, Callback: %s, "
                             "Args: %s", event, ev_type, callback, kwargs)
            return
        if self._debug:
            self.debug_log("Event: ===='%s'==== Type: %s, Callback: %s, "
                           "Args: %s", event, ev_type, callback, kwargs)
        elif self._info and not kwargs.get("_silent", False):
            self.info_log("Event: ======'%s'====== Args=%s", event, kwargs)

        # fast path for events without handler
        if not callback and not self.monitor_events and event not in self.registered_handlers:
            return

        if not self.event_queue and hasattr(self.machine.clock, "loop"):
            self.machine.clock.loop.call_soon(self.process_event_queue)

        posted_event = PostedEvent(event, ev_type, callback, kwargs)

        if self.monitor_events and not kwargs.get("_silent", False):
            self.machine.bcp.interface.monitor_posted_event(posted_event)

        self.event_queue.append(posted_event)
        if self._debug:
            self.debug_log("+============= EVENTS QUEUE =============")
            for this_event in list(self.event_queue):    # type: ignore
                self.debug_log("| %s, %s, %s, %s", this_event[0], this_event[1],
                               this_event[2], this_event[3])
            self.debug_log("+========================================")

    async def _run_handlers_sequential(self, event: str, callback, kwargs: dict) -> None:
        """Run all handlers for an event."""
        if self._debug:
            self.debug_log("^^^^ Processing queue event '%s'. Callback: %s,"
                           " Args: %s", event, callback, kwargs)

        # all handlers may have been removed in the meantime
        if event not in self.registered_handlers:
            return

        # Now let's call the handlers one-by-one, including any kwargs
        for handler in self.registered_handlers[event][:]:
            # use slice above so we don't process new handlers that came
            # in while we were processing previous handlers

            # merge the post's kwargs with the registered handler's kwargs
            # in case of conflict, handlers kwargs will win
            merged_kwargs = dict(list(kwargs.items()) + list(handler.kwargs.items()))

            # if condition exists and is not true skip
            if handler.condition is not None and not handler.condition.evaluate(merged_kwargs):
                continue

            # log if debug is enabled and this event is not the timer tick
            if self._debug:
                self.debug_log("%s (priority: %s) responding to event '%s'"
                               " with args %s",
                               self._pretty_format_handler(handler.callback), handler.priority,
                               event, merged_kwargs)

            # call the handler and save the results

            try:
                queue = merged_kwargs.pop('queue')
            except KeyError:
                queue = QueuedEvent(self.debug_log)

            handler.callback(queue=queue, **merged_kwargs)

            if queue.waiter:
                queue.event = asyncio.Event()
                await queue.event.wait()

        if self._debug:
            self.debug_log("vvvv Finished queue event '%s'. Callback: %s. "
                           "Args: %s", event, callback, kwargs)

        if callback:
            callback(**kwargs)

    def _run_handlers(self, event: str, ev_type: Optional[str], kwargs: dict) -> Any:
        """Run all handlers for an event."""
        result = None
        for handler in self.registered_handlers[event][:]:
            # use slice above so we don't process new handlers that came
            # in while we were processing previous handlers

            if '_min_priority' in kwargs and handler.blocking_facility and \
                (kwargs['_min_priority']['all'] > handler.priority or (
                    handler.blocking_facility in kwargs['_min_priority'] and
                    kwargs['_min_priority'][handler.blocking_facility] > handler.priority)):
                continue

            if handler.kwargs and kwargs:
                # merge the post's kwargs with the registered handler's kwargs
                # in case of conflict, handler kwargs will win
                merged_kwargs = dict(list(kwargs.items()) + list(handler.kwargs.items()))
            elif handler.kwargs:
                merged_kwargs = handler.kwargs
            else:
                merged_kwargs = kwargs

            # if condition exists and is not true skip
            if handler.condition is not None and not handler.condition.evaluate(merged_kwargs):
                continue

            if self._debug:
                self.debug_log("%s (priority: %s) responding to event '%s'"
                               " with args %s",
                               self._pretty_format_handler(handler.callback), handler.priority,
                               event, merged_kwargs)

            # call the handler and save the results
            try:
                result = handler.callback(**merged_kwargs)
            except Exception as e:
                raise EventHandlerException(
                    "Exception while processing {} for event {}. {}".format(handler, event, e)) from e

            # If whatever handler we called returns False, we stop
            # processing the remaining handlers for boolean or queue events
            if ev_type == 'boolean' and result is False:
                # add a False result so our callback knows something failed
                kwargs['ev_result'] = False

                if self._debug:
                    self.debug_log("Aborting future event processing")
                break

            if ev_type == 'relay' and isinstance(result, dict):
                kwargs.update(result)
            elif isinstance(result, dict) and '_min_priority' in result:
                kwargs['_min_priority'] = result['_min_priority']

        return result

    def _process_queue_event(self, event: str, callback, **kwargs: dict):
        """Handle queue events."""
        if event not in self.registered_handlers:
            # fast path if there are not handlers
            self.callback_queue.append((callback, kwargs))
        else:
            task = asyncio.create_task(self._run_handlers_sequential(event, callback, kwargs))
            task.add_done_callback(self._queue_task_done)
            self._queue_tasks.append(task)

    def stop(self):
        """Stop all ongoing event handlers."""
        self._stopped = True
        for handler in self._queue_tasks:
            handler.cancel()

    def _queue_task_done(self, future):
        """Remove queue task from list and evaluate result."""
        future.result()
        self._queue_tasks.remove(future)

    def _process_event(self, event: str, ev_type: Optional[str], callback=None, **kwargs: dict) -> None:
        # Internal method which actually handles the events. Don't call this.

        result = None
        if self._debug:
            self.debug_log("^^^^ Processing event '%s'. Type: %s, Callback: %s,"
                           " Args: %s", event, ev_type, callback, kwargs)

        # Now let's call the handlers one-by-one, including any kwargs
        if event in self.registered_handlers:
            result = self._run_handlers(event, ev_type, kwargs)

        if self._debug:
            self.debug_log("vvvv Finished event '%s'. Type: %s. Callback: %s. "
                           "Args: %s", event, ev_type, callback, kwargs)

        if callback:
            # For event types other than queue, we'll handle the callback here.
            # Queue events with active waits will do the callback when the
            # waits clear

            if result:
                # if our last handler returned something, add it to kwargs
                kwargs['ev_result'] = result

            self.callback_queue.append((callback, kwargs))

    def process_event_queue(self) -> None:
        """Check if there are any other events that need to be processed, and then process them."""
        inner_queue = deque()   # type: Deque[Deque[PostedEvent]]
        while self.event_queue or self.callback_queue:
            # first process all events. if they post more events we will
            # process them in the same loop.
            if self.event_queue:
                next_queue = self.event_queue
                self.event_queue = deque()
                while next_queue:
                    # remember the previous queue since events might be posted in this handler

                    event = next_queue.popleft()
                    if not next_queue and inner_queue:
                        next_queue = inner_queue.popleft()

                    if event.type == "queue":
                        self._process_queue_event(event=event[0],
                                                  callback=event[2],
                                                  **event[3])
                    else:
                        self._process_event(event=event[0],
                                            ev_type=event[1],
                                            callback=event[2],
                                            **event[3])

                    # make sure the handler created during this handler are called first
                    if self.event_queue:
                        inner_queue.appendleft(next_queue)
                        next_queue = self.event_queue
                        self.event_queue = deque()

            # when all events are processed run the _last_ callback. afterwards
            # continue with the loop and run all events. this makes sure all
            # events are completed before running the callback
            if self.callback_queue:
                callback, kwargs = self.callback_queue.pop()
                callback(**kwargs)


class QueuedEvent:

    """Base class for an event queue which is created each time a queue event is called."""

    def __init__(self, debug_log: Callable[[str], None]) -> None:
        """Initialize QueueEvent."""
        self.debug_log = debug_log
        self.waiter = False
        self.event = None   # type: Optional[asyncio.Event]

    def __repr__(self):
        """Return str representation."""
        return '<QueuedEvent>'

    def wait(self) -> None:
        """Register a wait for this QueueEvent."""
        if self.waiter:
            raise AssertionError("Double lock")
        self.waiter = True
        self.debug_log("QueuedEvent: Registering a wait.")

    def clear(self) -> None:
        """Clear a wait."""
        if not self.waiter:
            raise AssertionError("Not locked")

        self.waiter = False

        # in case this is async we release the lock
        if self.event:
            self.event.set()

    def is_empty(self) -> bool:
        """Return true if unlocked."""
        return not self.waiter


def event_handler(relative_priority):
    """Decorate an event handler."""
    def decorator(func):
        """Decorate a function with relative priority."""
        func.relative_priority = relative_priority
        return func

    return decorator
