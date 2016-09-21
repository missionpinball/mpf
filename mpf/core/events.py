"""Classes for the EventManager and QueuedEvents."""

import logging
from collections import deque, namedtuple
import uuid

import asyncio
from functools import partial

EventHandlerKey = namedtuple("EventHandlerKey", ["key", "event"])
RegisteredHandler = namedtuple("RegisteredHandler", ["callback", "priority", "kwargs", "key"])
PostedEvent = namedtuple("PostedEvent", ["event", "type", "callback", "kwargs"])


class EventManager(object):

    """Handles all the events and manages the handlers in MPF."""

    def __init__(self, machine):
        """Initialise EventManager."""
        self.log = logging.getLogger("Events")
        self.machine = machine
        self.registered_handlers = {}   # type: {str: [RegisteredHandler]}
        self.event_queue = deque([])
        self.callback_queue = deque([])

        self.debug = True

    def add_handler(self, event, handler, priority=1, **kwargs):
        """Register an event handler to respond to an event.

        If you add a handlers for an event for which it has already been
        registered, the new one will overwrite the old one. This is useful for
        changing priorities of existing handlers. Also it's good to know that
        you can safely add a handler over and over.

        Args:
            event: String name of the event you're adding a handler for. Since
                events are text strings, they don't have to be pre-defined.
                Note that all event strings will be converted to lowercase.
            handler: The method that will be called when the event is fired.
            priority: An arbitrary integer value that defines what order the
                handlers will be called in. The default is 1, so if you have a
                handler that you want to be called first, add it here with a
                priority of 2. (Or 3 or 10 or 100000.) The numbers don't matter.
                They're called from highest to lowest. (i.e. priority 100 is
                called before priority 1.)
            **kwargs: Any any additional keyword/argument pairs entered here
                will be attached to the handler and called whenever that handler
                is called. Note these are in addition to kwargs that could be
                passed as part of the event post. If there's a conflict, the
                event-level ones will win.

        Returns:
            A GUID reference to the handler which you can use to later remove
            the handler via ``remove_handler_by_key``.

        For example:
        ``handler_list.append(events.add_handler('ev', self.test))``

        Then later to remove all the handlers that a module added, you could:
        for handler in handler_list:
        ``events.remove_handler(handler)``
        """
        if not callable(handler):
            raise ValueError('Cannot add handler "{}" for event "{}". Did you '
                             'accidentally add parenthesis to the end of the '
                             'handler you passed?'.format(handler, event))

        event = event.lower()

        # Add an entry for this event if it's not there already
        if event not in self.registered_handlers:
            self.registered_handlers[event] = []

        key = uuid.uuid4()

        # An event 'handler' in our case is a tuple with 4 elements:
        # the handler method, priority, dict of kwargs, & uuid key

        self.registered_handlers[event].append(RegisteredHandler(handler, priority, kwargs, key))
        if self.debug:
            try:
                self.log.debug("Registered %s as a handler for '%s', priority: %s, "
                               "kwargs: %s",
                               (str(handler).split(' '))[2], event, priority, kwargs)
            except IndexError:
                pass

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        self.registered_handlers[event].sort(key=lambda x: x.priority, reverse=True)

        return EventHandlerKey(key, event)

    def replace_handler(self, event, handler, priority=1, **kwargs):
        """Check to see if a handler (optionally with kwargs) is registered for an event and replaces it if so.

        Args:
            event: The event you want to check to see if this handler is
                registered for. This string will be converted to lowercase.
            handler: The method of the handler you want to check.
            priority: Optional priority of the new handler that will be
                registered.
            **kwargs: The kwargs you want to check and the kwatgs that will be
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

        self.add_handler(event, handler, priority, **kwargs)

    def remove_handler(self, method):
        """Remove an event handler from all events a method is registered to handle.

        Args:
            method : The method whose handlers you want to remove.
        """
        events_to_delete_if_empty = []
        for event, handler_list in self.registered_handlers.items():
            for handler_tup in handler_list[:]:  # copy via slice
                if handler_tup[0] == method:
                    handler_list.remove(handler_tup)
                    if self.debug:
                        self.log.debug("Removing method %s from event %s", (str(method).split(' '))[2], event)
                    events_to_delete_if_empty.append(event)

        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handler_by_event(self, event, handler):
        """Remove the handler you pass from the event you pass.

        Args:
            event: The name of the event you want to remove the handler from.
                This string will be converted to lowercase.
            handler: The handler method you want to remove.

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
                    if self.debug:
                        self.log.debug("Removing method %s from event %s", (str(handler).split(' '))[2], event)
                    events_to_delete_if_empty.append(event)

        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handler_by_key(self, key: EventHandlerKey):
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
                if self.debug:
                    self.log.debug("Removing method %s from event %s", (str(handler_tup[0]).split(' '))[2], key.event)
                events_to_delete_if_empty.append(key.event)
        for event in events_to_delete_if_empty:
            self._remove_event_if_empty(event)

    def remove_handlers_by_keys(self, key_list):
        """Remove multiple event handlers based on a passed list of keys.

        Args:
            key_list: A list of keys of the handlers you want to remove
        """
        for key in key_list:
            self.remove_handler_by_key(key)

    def _remove_event_if_empty(self, event):
        # Checks to see if the event doesn't have any more registered handlers,
        # removes it if so.

        if event not in self.registered_handlers:
            return

        if not self.registered_handlers[event]:  # if value is empty list
            del self.registered_handlers[event]
            if self.debug:
                self.log.debug("Removing event %s since there are no more"
                               " handlers registered for it", event)

    def wait_for_event(self, event_name: str):
        """Wait for event."""
        return self.wait_for_any_event([event_name])

    def wait_for_any_event(self, event_names: [str]):
        """Wait for any event from event_names."""
        future = asyncio.Future(loop=self.machine.clock.loop)
        keys = []
        for event_name in event_names:
            keys.append(self.add_handler(event_name, partial(self._wait_handler,
                                                             _future=future,
                                                             _keys=keys,
                                                             event=event_name)))
        return future

    def _wait_handler(self, _future: asyncio.Future, _keys: [str], **kwargs):
        for key in _keys:
            self.remove_handler_by_key(key)

        if _future.cancelled():
            return
        _future.set_result(result=kwargs)

    def does_event_exist(self, event_name):
        """Check to see if any handlers are registered for the event name that is passed.

        Args:
            event_name : The string name of the event you want to check. This
                string will be converted to lowercase.

        Returns:
            True or False
        """
        return event_name.lower() in self.registered_handlers

    def post(self, event, callback=None, **kwargs):
        """Post an event which causes all the registered handlers to be called.

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registed. (Higher priority
        values will be processed first.)

        Args:
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it. Note that this event name will be converted
                to lowercase.
            callback: An optional method which will be called when the final
                handler is done processing this event. Default is None.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)

        """
        self._post(event, ev_type=None, callback=callback, **kwargs)

    def post_boolean(self, event, callback=None, **kwargs):
        """Post an boolean event which causes all the registered handlers to be called one-by-one.

        Boolean events differ from regular events in that
        if any handler returns False, the remaining handlers will not be
        called.

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registed. (Higher priority
        values will be processed first.)

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
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)
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
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)
        """
        self._post(event, ev_type='queue', callback=callback, **kwargs)

    def post_relay(self, event, callback=None, **kwargs):
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
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)

        Events are processed serially (e.g. one at a time), so if the event
        core is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registed. (Higher priority
        values will be processed first.)

        Relay events differ from standard events in that the resulting kwargs
        from one handler are passed to the next handler. (In other words,
        stanard events mean that all the handlers get the same initial kwargs,
        whereas relay events "relay" the resulting kwargs from one handler to
        the next.)
        """
        self._post(event, ev_type='relay', callback=callback, **kwargs)

    def _post(self, event, ev_type, callback, **kwargs):

        event = event.lower()

        if self.debug:
            self.log.debug("^^^^ Posted event '%s'. Type: %s, Callback: %s, "
                           "Args: %s", event, ev_type, callback, kwargs)

        if not self.event_queue and hasattr(self.machine.clock, "loop"):
            self.machine.clock.loop.call_soon(self.process_event_queue)

        self.event_queue.append(PostedEvent(event, ev_type, callback, kwargs))
        if self.debug:
            self.log.debug("============== EVENTS QUEUE =============")
            for event in list(self.event_queue):
                self.log.debug("%s, %s, %s, %s", event[0], event[1],
                               event[2], event[3])
            self.log.debug("=========================================")

    def _process_event(self, event, ev_type, callback=None, **kwargs):
        # Internal method which actually handles the events. Don't call this.

        result = None
        queue = None
        if self.debug:
            self.log.debug("^^^^ Processing event '%s'. Type: %s, Callback: %s,"
                           " Args: %s", event, ev_type, callback, kwargs)

        # Now let's call the handlers one-by-one, including any kwargs
        if event in self.registered_handlers:

            if ev_type == 'queue' and callback:
                queue = QueuedEvent(callback, **kwargs)
                kwargs['queue'] = queue

            for handler in self.registered_handlers[event][:]:
                # use slice above so we don't process new handlers that came
                # in while we were processing previous handlers

                # merge the post's kwargs with the registered handler's kwargs
                # in case of conflict, posts kwargs will win
                merged_kwargs = dict(list(handler.kwargs.items()) + list(kwargs.items()))

                # log if debug is enabled and this event is not the timer tick
                if self.debug:
                    try:
                        self.log.debug("%s (priority: %s) responding to event '%s'"
                                       " with args %s",
                                       (str(handler.callback).split(' ')), handler.priority,
                                       event, merged_kwargs)
                    except IndexError:
                        pass

                # call the handler and save the results
                result = handler.callback(**merged_kwargs)

                # If whatever handler we called returns False, we stop
                # processing the remaining handlers for boolean or queue events
                if ((ev_type == 'boolean' or ev_type == 'queue') and
                        result is False):

                    # add a False result so our callback knows something failed
                    kwargs['ev_result'] = False

                    if self.debug:
                        self.log.debug("Aborting future event processing")

                    break

                elif ev_type == 'relay' and isinstance(result, dict):
                    kwargs.update(result)

        if self.debug:
            self.log.debug("vvvv Finished event '%s'. Type: %s. Callback: %s. "
                           "Args: %s", event, ev_type, callback, kwargs)

        if ev_type == 'queue':
            self._handle_queue(queue, callback, kwargs)
        elif callback:
            # For event types other than queue, we'll handle the callback here.
            # Queue events with active waits will do the callback when the
            # waits clear

            if result:
                # if our last handler returned something, add it to kwargs
                kwargs['ev_result'] = result

            self.callback_queue.append((callback, kwargs))

    def _handle_queue(self, queue, callback, kwargs):
        if callback and not queue:
            # If this was a queue event but there were no registered handlers,
            # then we need to do the callback now
            self.callback_queue.append((callback, kwargs))

        elif queue and queue.is_empty():
            # If we had a queue event that had handlers and a queue was created
            # we need to see if any the queue is empty now, and if so, do the
            # callback

            del kwargs['queue']  # ditch this since we don't need it now

            if queue.callback:
                # if there's still a callback, that means it wasn't called yet
                self.callback_queue.append((queue.callback, kwargs))
        elif queue and not queue.is_empty():
            queue.event_finished()

    def process_event_queue(self):
        """Check if there are any other events that need to be processed, and then process them."""
        while len(self.event_queue) > 0 or len(self.callback_queue) > 0:
            # first process all events. if they post more events we will
            # process them in the same loop.
            while len(self.event_queue) > 0:
                event = self.event_queue.popleft()
                self._process_event(event=event[0],
                                    ev_type=event[1],
                                    callback=event[2],
                                    **event[3])

            # when all events are processed run the _last_ callback. afterwards
            # continue with the loop and run all events. this makes sure all
            # events are completed before running the callback
            if len(self.callback_queue) > 0:
                callback, kwargs = self.callback_queue.pop()
                callback(**kwargs)


class QueuedEvent(object):

    """Base class for an event queue which is created each time a queue event is called."""

    def __init__(self, callback, **kwargs):
        """Initialise QueueEvent."""
        self.log = logging.getLogger("Queue")

        self.debug = True

        if self.debug:
            self.log.debug("Creating an event queue. Callback: %s Args: %s",
                           callback, kwargs)
        self.callback = callback
        self.kwargs = kwargs
        self.num_waiting = 0
        self._is_event_finished = False

    def __repr__(self):
        """Return str representation."""
        return '<QueuedEvent for callback {}>'.format(self.callback)

    def event_finished(self):
        """Return true if event is finished."""
        self._is_event_finished = True

    def wait(self):
        """Register a wait for this QueueEvent."""
        self.num_waiting += 1
        if self.debug:
            self.log.debug("Registering a wait. Current count: %s",
                           self.num_waiting)

    def clear(self):
        """Clear a wait.

        If the number of waits drops to 0, the callbacks will be called.
        """
        self.num_waiting -= 1
        if self.debug:
            self.log.debug("Clearing a wait. Current count: %s",
                           self.num_waiting)
        if not self.num_waiting and self._is_event_finished:
            if self.debug:
                self.log.debug("Queue is empty. Calling %s", self.callback)
            # del self.kwargs['queue']  # ditch this since we don't need it now
            callback = self.callback
            self.callback = None
            callback(**self.kwargs)

    def kill(self):
        """Kill this QueuedEvent by removing all waits.

        Does not process the callback.
        """
        self.num_waiting = 0

    def is_empty(self):
        """Check to see if this QueuedEvent has any waits.

        Returns:
            True is there are 1 or more waits, False if there are no more
            waits.

        """
        return not self.num_waiting
