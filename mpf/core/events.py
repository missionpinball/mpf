"""Classes for the EventManager and QueuedEvents."""
import inspect
from collections import deque, namedtuple
import uuid

import asyncio
from enum import Enum
from functools import partial
from unittest.mock import MagicMock

from typing import Dict, Any, Tuple, Optional, Generator, Callable, List

from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController
    from mpf.core.placeholder_manager import BaseTemplate
    from typing import Deque

EventHandlerKey = namedtuple("EventHandlerKey", ["key", "event"])
RegisteredHandler = namedtuple("RegisteredHandler", ["callback", "priority", "kwargs", "key", "condition",
                                                     "blocking_facility"])
PostedEvent = namedtuple("PostedEvent", ["event", "type", "callback", "kwargs"])


class EventManager(MpfController):

    """Handles all the events and manages the handlers in MPF."""

    config_name = "event_manager"

    def __init__(self, machine: "MachineController") -> None:
        """Initialize EventManager."""
        super().__init__(machine)

        self.registered_handlers = {}       # type: Dict[str, List[RegisteredHandler]]
        self.event_queue = deque([])        # type: Deque[PostedEvent]
        self.callback_queue = deque([])     # type: Deque[Tuple[Any, dict]]
        self.monitor_events = False
        self._queue_tasks = []              # type: List[asyncio.Task]

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

    def get_event_and_condition_from_string(self, event_string: str) -> Tuple[str, Optional["BaseTemplate"]]:
        """Parse an event string to divide the event name from a possible placeholder / conditional in braces.

        Args:
            event_string: String to parse

        Returns:
            2-item tuple:
                First item is the event name, cleaned up a by converting it
                to lowercase.

                Second item is the condition (A BoolTemplate instance) if it
                exists, or None if it doesn't.

        """
        if event_string.find("{") > 0 and event_string[-1:] == "}":
            return (event_string[0:event_string.find("{")].lower(),
                    self.machine.placeholder_manager.build_bool_template(
                        event_string[event_string.find("{") + 1:-1]))

        else:
            return event_string.lower(), None

    def add_async_handler(self, event: str, handler: Any, priority: int = 1, blocking_facility: Any = None,
                          **kwargs) -> EventHandlerKey:
        """Register a coroutine as event handler."""
        return self.add_handler(event, partial(self._async_handler_coroutine, handler), priority, blocking_facility,
                                **kwargs)

    def _async_handler_coroutine(self, _coroutine, queue, **kwargs):
        queue.wait()
        task = self.machine.clock.loop.create_task(_coroutine(**kwargs))
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
            event: String name of the event you're adding a handler for. Since
                events are text strings, they don't have to be pre-defined.
                Note that all event strings will be converted to lowercase.
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
            **kwargs: Any any additional keyword/argument pairs entered here
                will be attached to the handler and called whenever that
                handler is called. Note these are in addition to kwargs that
                could be passed as part of the event post. If there's a
                conflict, the event-level ones will win.

        Returns:
            A GUID reference to the handler which you can use to later remove
            the handler via ``remove_handler_by_key``.

        For example:

        .. code::

            my_handler = self.machine.events.add_handler('ev', self.test))

        Then later to remove all the handlers that a module added, you could:
        for handler in handler_list:
        ``events.remove_handler(my_handler)``
        """
        if not callable(handler):
            raise ValueError('Cannot add handler "{}" for event "{}". Did you '
                             'accidentally add parenthesis to the end of the '
                             'handler you passed?'.format(handler, event))

        sig = inspect.signature(handler)
        if 'kwargs' not in sig.parameters:
            raise AssertionError("Handler {} for event '{}' is missing **kwargs. Actual signature: {}".format(
                handler, event, sig))

        if sig.parameters['kwargs'].kind != inspect.Parameter.VAR_KEYWORD:
            raise AssertionError("Handler {} for event '{}' param kwargs is missing '**'. Actual signature: {}".format(
                handler, event, sig))

        event, condition = self.get_event_and_condition_from_string(event)

        # Add an entry for this event if it's not there already
        if event not in self.registered_handlers:
            self.registered_handlers[event] = []

        key = uuid.uuid4()

        # An event 'handler' in our case is a tuple with 4 elements:
        # the handler method, priority, dict of kwargs, & uuid key
        if hasattr(handler, "relative_priority") and not isinstance(handler, MagicMock):
            priority += handler.relative_priority

        self.registered_handlers[event].append(RegisteredHandler(handler, priority, kwargs, key, condition,
                                                                 blocking_facility))

        try:
            self.debug_log("Registered %s as a handler for '%s', priority: %s, "
                           "kwargs: %s",
                           (str(handler).split(' '))[2], event, priority, kwargs)
        except IndexError:
            pass

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        self.registered_handlers[event].sort(key=lambda x: x.priority, reverse=True)

        if self._info_to_console or self._info_to_file or True:
            self._verify_handlers(event, self.registered_handlers[event])

        return EventHandlerKey(key, event)

    def _verify_handlers(self, event, sorted_handlers):
        """Verify that no races can happen."""
        if not sorted_handlers:
            return
        priority = -1
        devices = []
        for handler in sorted_handlers:
            # if priority is different we are fine
            if priority != handler.priority:
                priority = handler.priority
                devices = []

            # same priority order is random. check that is does not happen on one class
            if not inspect.ismethod(handler.callback):
                continue
            cls = handler.callback.__self__

            # noinspection PyProtectedMember
            # pylint: disable-msg=protected-access
            if hasattr(self.machine, "device_manager") and cls == self.machine.device_manager and \
                    handler.callback == self.machine.device_manager._control_event_handler:
                cls = (handler.kwargs["callback"].__self__, handler.kwargs["ms_delay"])

            if cls in devices:
                handlers = [h for h in sorted_handlers if h.priority == priority and
                            inspect.ismethod(h.callback) and
                            h.condition == handler.condition and
                            h.callback.__self__ == handler.callback.__self__]

                self.info_log(
                    "Duplicate handler for class {} on event {} with priority {}. Handlers: {}".format(
                        cls, event, priority, handlers
                    )
                )
            devices.append(cls)

    def replace_handler(self, event: str, handler: Any, priority: int = 1,
                        **kwargs: dict) -> EventHandlerKey:
        """Check to see if a handler (optionally with kwargs) is registered for an event and replaces it if so.

        Args:
            event: The event you want to check to see if this handler is
                registered for. This string will be converted to lowercase.
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
        event = event.lower()

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

    def remove_handler(self, method: Any) -> None:
        """Remove an event handler from all events a method is registered to handle.

        Args:
            method : The method whose handlers you want to remove.
        """
        events_to_delete_if_empty = []
        for event, handler_list in self.registered_handlers.items():
            for handler_tup in handler_list[:]:  # copy via slice
                if handler_tup[0] == method:
                    handler_list.remove(handler_tup)
                    self.debug_log("Removing method %s from event %s", (str(method).split(' '))[2], event)
                    events_to_delete_if_empty.append(event)

        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handler_by_event(self, event: str, handler: Any) -> None:
        """Remove the handler you pass from the event you pass.

        Args:
            event: The name of the event you want to remove the handler from.
                This string will be converted to lowercase.
            handler:
                The handler method you want to remove.

        Note that keyword arguments for the handler are not taken into
        consideration. In other words, this method only removes the registered
        handler / event combination, regardless of whether the keyword
        arguments match or not.
        """
        event = event.lower()

        events_to_delete_if_empty = []
        if event in self.registered_handlers:
            for handler_tup in self.registered_handlers[event][:]:
                if handler_tup[0] == handler:
                    self.registered_handlers[event].remove(handler_tup)
                    self.debug_log("Removing method %s from event %s", (str(handler).split(' '))[2], event)
                    events_to_delete_if_empty.append(event)

        for this_event in events_to_delete_if_empty:
            self._remove_event_if_empty(this_event)

    def remove_handler_by_key(self, key: EventHandlerKey) -> None:
        """Remove a registered event handler by key.

        Args:
            key: The key of the handler you want to remove
        """
        if key.event not in self.registered_handlers:
            return
        events_to_delete_if_empty = []
        for handler_tup in self.registered_handlers[key.event][:]:  # copy via slice
            if handler_tup.key == key.key:
                self.registered_handlers[key.event].remove(handler_tup)
                self.debug_log("Removing method %s from event %s", (str(handler_tup[0]).split(' '))[2], key.event)
                events_to_delete_if_empty.append(key.event)
        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handlers_by_keys(self, key_list: List[EventHandlerKey]) -> None:
        """Remove multiple event handlers based on a passed list of keys.

        Args:
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
            self.debug_log("Removing event %s since there are no more"
                           " handlers registered for it", event)

    def wait_for_event(self, event_name: str) -> asyncio.Future:
        """Wait for event."""
        return self.wait_for_any_event([event_name])

    def wait_for_any_event(self, event_names: List[str]) -> asyncio.Future:
        """Wait for any event from event_names."""
        future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future
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
            event_name : The string name of the event you want to check. This
                string will be converted to lowercase.

        Returns:
            True or False
        """
        return event_name.lower() in self.registered_handlers

    @staticmethod
    def _set_result(_future, **kwargs):
        if not _future.done():
            _future.set_result(kwargs)

    def post_async(self, event: str, **kwargs: dict) -> asyncio.Future:
        """Post event and wait until all handlers are done."""
        future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future
        self.post(event, partial(self._set_result, _future=future), **kwargs)
        return future

    def post_relay_async(self, event: str, **kwargs: dict) -> asyncio.Future:
        """Post relay event, wait until all handlers are done and return result."""
        future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future
        self.post_relay(event, partial(self._set_result, _future=future), **kwargs)
        return future

    def post_queue_async(self, event: str, **kwargs: dict) -> asyncio.Future:
        """Post queue event, wait until all handlers are done and locks are released."""
        future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future
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
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it. Note that this event name will be converted
                to lowercase.
            callback: An optional method which will be called when the final
                handler is done processing this event. Default is None.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (The event manager will enforce that
                handlers have ``**kwargs`` in their signatures when they're
                registered to prevent run-time crashes from unexpected kwargs
                that were included in ``post()`` calls.
        """
        self._post(event, ev_type=None, callback=callback, **kwargs)

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
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it. Note that this event name will be converted
                to lowercase.
            callback: An optional method which will be called when the final
                handler is done processing this event. Default is None. If
                any handler returns False and cancels this boolean event, the
                callback will still be called, but a new kwarg ev_result=False
                will be passed to it.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler.
        """
        self._post(event, ev_type='boolean', callback=callback, **kwargs)

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
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it. Note that this event name will be converted
                to lowercase.
            callback: The method which will be called when the final
                handler is done processing this event and any handlers that
                registered waits have cleared their waits.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add ``**kwargs`` to your handler
                methods if certain ones don't need them.)

        Examples:
            Post the queue event called *pizza_time*, and then call
            ``self.pizza_done`` when done:

            .. code::

                 self.machine.events.post_queue('pizza_time', self.pizza_done)

        """
        self._post(event, ev_type='queue', callback=callback, **kwargs)

    def post_relay(self, event: str, callback=None, **kwargs) -> None:
        """Post a relay event which causes all the registered handlers to be called.

        A dictionary can be passed from handler-to-handler and modified
        as needed.

        Args:
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it. Note that this event name will be converted
                to lowercase.
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
        self._post(event, ev_type='relay', callback=callback, **kwargs)

    def _post(self, event: str, ev_type: Optional[str], callback, **kwargs: dict) -> None:

        event = event.lower()

        if self._debug_to_console or self._debug_to_file:
            self.debug_log("Event: ===='%s'==== Type: %s, Callback: %s, "
                           "Args: %s", event, ev_type, callback, kwargs)
        elif not kwargs.get("_silent", False):
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
        self.debug_log("+============= EVENTS QUEUE =============")
        for this_event in list(self.event_queue):    # type: ignore
            self.debug_log("| %s, %s, %s, %s", this_event[0], this_event[1],
                           this_event[2], this_event[3])
        self.debug_log("+========================================")

    @asyncio.coroutine
    def _run_handlers_sequential(self, event: str, callback, kwargs: dict) -> Generator[int, None, None]:
        """Run all handlers for an event."""
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
            try:
                self.debug_log("%s (priority: %s) responding to event '%s'"
                               " with args %s",
                               (str(handler.callback).split(' ')), handler.priority,
                               event, merged_kwargs)
            except IndexError:
                pass

            # call the handler and save the results

            try:
                queue = merged_kwargs.pop('queue')
            except KeyError:
                queue = QueuedEvent(self.debug_log)

            handler.callback(queue=queue, **merged_kwargs)

            if queue.waiter:
                queue.event = asyncio.Event(loop=self.machine.clock.loop)
                yield from queue.event.wait()

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

            # merge the post's kwargs with the registered handler's kwargs
            # in case of conflict, handler kwargs will win
            merged_kwargs = dict(list(kwargs.items()) + list(handler.kwargs.items()))

            # if condition exists and is not true skip
            if handler.condition is not None and not handler.condition.evaluate(merged_kwargs):
                continue

            try:
                self.debug_log("%s (priority: %s) responding to event '%s'"
                               " with args %s",
                               (str(handler.callback).split(' ')), handler.priority,
                               event, merged_kwargs)
            except IndexError:
                pass

            # call the handler and save the results
            result = handler.callback(**merged_kwargs)

            # If whatever handler we called returns False, we stop
            # processing the remaining handlers for boolean or queue events
            if ev_type == 'boolean' and result is False:
                # add a False result so our callback knows something failed
                kwargs['ev_result'] = False

                self.debug_log("Aborting future event processing")
                break

            elif ev_type == 'relay' and isinstance(result, dict):
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
            task = self.machine.clock.loop.create_task(self._run_handlers_sequential(event, callback, kwargs))
            task.add_done_callback(self._done)
            self._queue_tasks.append(task)

    def _done(self, future):
        """Remove queue task from list and evaluate result."""
        future.result()
        self._queue_tasks.remove(future)

    def _process_event(self, event: str, ev_type: Optional[str], callback=None, **kwargs: dict) -> None:
        # Internal method which actually handles the events. Don't call this.

        result = None
        self.debug_log("^^^^ Processing event '%s'. Type: %s, Callback: %s,"
                       " Args: %s", event, ev_type, callback, kwargs)

        # Now let's call the handlers one-by-one, including any kwargs
        if event in self.registered_handlers:
            result = self._run_handlers(event, ev_type, kwargs)

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
        while self.event_queue or self.callback_queue:
            # first process all events. if they post more events we will
            # process them in the same loop.
            while self.event_queue:
                event = self.event_queue.popleft()
                if event.type == "queue":
                    self._process_queue_event(event=event[0],
                                              callback=event[2],
                                              **event[3])
                else:
                    self._process_event(event=event[0],
                                        ev_type=event[1],
                                        callback=event[2],
                                        **event[3])

            # when all events are processed run the _last_ callback. afterwards
            # continue with the loop and run all events. this makes sure all
            # events are completed before running the callback
            if self.callback_queue:
                callback, kwargs = self.callback_queue.pop()
                callback(**kwargs)


class QueuedEvent(object):

    """Base class for an event queue which is created each time a queue event is called."""

    def __init__(self, debug_log: Callable[[str], None]) -> None:
        """Initialize QueueEvent."""
        self.debug_log = debug_log
        self.waiter = False
        self.event = None   # type: asyncio.Event

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
