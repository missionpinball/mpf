"""Contains the base classes for the EventManager and QueuedEvents"""
# events.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import deque
import uuid


class EventManager(object):

    def __init__(self, machine):
        self.log = logging.getLogger("Events")
        self.machine = machine
        self.event_queue = []
        self.registered_handlers = {}
        self.busy = False
        self.queue = deque([])
        self.current_event = None
        self.debug = True  # logs all event activity except timer_ticks.

    def add_handler(self, event, handler, priority=1, **kwargs):
        """Registers an event handler to respond to an event.

        If you add a handlers for an event for which it has already been
        registered, the new one will overwrite the old one. This is useful for
        changing priorities of existing handlers. Also it's good to know that
        you can safely add a handler over and over.

        Args:
            event: String name of the event you're adding a handler for. Since
                events are text strings, they don't have to be pre-defined.
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

        # Add an entry for this event if it's not there already
        if not event in self.registered_handlers:
            self.registered_handlers[event] = []

        key = uuid.uuid4()

        # An event 'handler' in our case is a tuple with 4 elements:
        # the handler method, priority, dict of kwargs, & uuid key

        self.registered_handlers[event].append((handler, priority, kwargs, key))
        self.log.debug("Registered %s as a handler for '%s', priority: %s",
                       (str(handler).split(' '))[2], event, priority)

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        self.registered_handlers[event].sort(key=lambda x: x[1], reverse=True)

        return key

    def replace_handler(self, event, handler, priority=1, **kwargs):
        """Checks to see if a handler (optionally with kwargs) is registered for
        an event and replaces it if so.

        Args:
            event: The event you want to check to see if this handler is
                registered for.
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

        self.add_handler(self, event, handler, priority, **kwargs)

    def remove_handler(self, method):
        """Removes an event handler from all events a method is registered to
        handle.

        Args:
            method : The method whose handlers you want to remove.
        """

        for event, handler_list in self.registered_handlers.iteritems():
            for handler_tup in handler_list[:]:  # copy via slice
                if handler_tup[0] == method:
                    handler_list.remove(handler_tup)
                    self.log.debug("Removing method %s from event %s",
                                   (str(method).split(' '))[2], event)

        self._remove_event_if_empty(event)

    def remove_handler_by_event(self, event, handler):
        """Removes the handler you pass from the event you pass.

        Args:
            event: The name of the event you want to remove the handler from.
            handler: The handler method you want to remove.

        Note that keyword arguments for the handler are not taken into
        consideration. In other words, this method only removes the registered
        handler / event combination, regardless of whether the keyword
        arguments match or not.
        """

        if event in self.registered_handlers:
            for handler_tup in self.registered_handlers[event][:]:
                if handler_tup[0] == handler:
                    self.registered_handlers[event].remove(handler_tup)
                    self.log.debug("Removing method %s from event %s",
                                   (str(handler).split(' '))[2], event)

        self._remove_event_if_empty(event)

    def remove_handler_by_key(self, key):
        """Removes a registered event handler by key.

        Args:
            key: The key of the handler you want to remove
        """

        for event, handler_list in self.registered_handlers.iteritems():
            for handler_tup in handler_list[:]:  # copy via slice
                if handler_tup[3] == key:
                    handler_list.remove(handler_tup)
                    self.log.debug("Removing method %s from event %s",
                                   (str(handler_tup[0]).split(' '))[2], event)

        self._remove_event_if_empty(event)

    def remove_handlers_by_keys(self, key_list):
        """Removes multiple event handlers based on a passed list of keys

        Args:
            key_list: A list of keys of the handlers you want to remove
        """
        for key in key_list:
            self.remove_handler_by_key(key)

    def _remove_event_if_empty(self, event):
        # Checks to see if the event doesn't have any more registered handlers,
        # removes it if so.

        if not self.registered_handlers[event]:  # if value is empty list
                del self.registered_handlers[event]
                self.log.debug("Removing event %s since there are no more"
                               " handlers registered for it", event)

    def does_event_exist(self, event_name):
        """Checks to see if any handlers are registered for the event name that
        is passed.

        Args:
            event_name : The string name of the event you want to check

        Returns:
            True or False

        """

        if event_name in self.registered_handlers:
            return True
        else:
            return False

    def post(self, event, callback=None, **kwargs):
        """Posts an event which causes all the registered handlers to be
        called.

        Events are processed serially (e.g. one at a time), so if the event
        system is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registed. (Higher priority
        values will be processed first.)

        Args:
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            callback: An optional method which will be called when the final
                handler is done processing this event. Default is None.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)

        """

        self._post(event, ev_type=None, callback=callback, **kwargs)

    def post_boolean(self, event, callback=None, **kwargs):
        """Posts an boolean event which causes all the registered handlers to
        be called one-by-one. Boolean events differ from regular events in that
        if any handler returns False, the remaining handlers will not be
        called.

        Events are processed serially (e.g. one at a time), so if the event
        system is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registed. (Higher priority
        values will be processed first.)

        Args:
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
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)

        """
        self._post(event, ev_type='boolean', callback=callback, **kwargs)

    def post_queue(self, event, callback, **kwargs):
        """Posts a queue event which causes all the registered handlers to be
        called.

        Queue events differ from standard events in that individual handlers
        are given the option to register a "wait", and the callback will not be
        called until any handler(s) that registered a wait will have to release
        that wait. Once all the handlers release their waits, the callback is
        called.

        Events are processed serially (e.g. one at a time), so if the event
        system is in the process of handling another event, this event is
        added to a queue and processed after the current event is done.

        You can control the order the handlers will be called by optionally
        specifying a priority when the handlers were registed. (Higher priority
        values will be processed first.)

        Args:
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
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
        """Posts a relay event which causes all the registered handlers to be
        called. A dictionary can be passed from handler-to-handler and modified
        as needed.

        Args:
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            callback: The method which will be called when the final handler is
                done processing this event. Default is None.
            **kwargs: One or more options keyword/value pairs that will be
                passed to each handler. (Just make sure your handlers are
                expecting them. You can add **kwargs to your handler methods if
                certain ones don't need them.)

        Events are processed serially (e.g. one at a time), so if the event
        system is in the process of handling another event, this event is
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
        if self.debug and event != 'timer_tick':
            # Use friendly_kwargs so the logger shows a "friendly" name of the
            # callback handler instead of the bound method object reference.
            friendly_kwargs = dict(kwargs)
            if 'callback' in kwargs:
                friendly_kwargs['callback'] = \
                    (str(kwargs['callback']).split(' '))[2]
            self.log.debug("^^^^ Posted event '%s'. Type: %s, Callback: %s, "
                           "Args: %s", event, ev_type, callback,
                           friendly_kwargs)
        if not self.busy:
            self._process_event(event, ev_type, callback, **kwargs)
        else:

            self.log.debug("XXXX Event '%s' is in progress. Added to the "
                           "queue.", self.current_event)
            self.queue.append((event, ev_type, callback, kwargs))

            self.log.debug("================== ACTIVE EVENTS ==================")
            for event in self.queue:
                self.log.debug("%s, %s, %s, %s", event[0], event[1], event[2],
                               event[3])
            self.log.debug("==================================================")

    def _process_event(self, event, ev_type, callback=None, **kwargs):
        # Internal method which actually handles the events. Don't call this.
        result = None
        queue = None
        if self.debug and event != 'timer_tick':
            # Show friendly callback name. See comment in post() above.
            friendly_kwargs = dict(kwargs)
            if 'callback' in kwargs:
                friendly_kwargs['callback'] = \
                    (str(kwargs['callback']).split(' '))[2]
            self.log.debug("^^^^ Processing event '%s'. Type: %s, Callback: %s,"
                           " Args: %s", event, ev_type, callback,
                           friendly_kwargs)

        # Now let's call the handlers one-by-one, including any kwargs
        if event in self.registered_handlers:
            self.busy = True
            self.current_event = event

            if ev_type == 'queue' and callback:
                queue = QueuedEvent(callback, **kwargs)
                kwargs['queue'] = queue

            for handler in self.registered_handlers[event][:]:
                # use slice above so we don't process new handlers that came
                # in while we were processing previous handlers

                # merge the post's kwargs with the registered handler's kwargs
                # in case of conflict, posts kwargs will win
                merged_kwargs = dict(handler[2].items() + kwargs.items())

                # log if debug is enabled and this event is not the timer tick
                if self.debug and event != 'timer_tick':
                    self.log.debug("%s (priority: %s) responding to event '%s' "
                                   "with args %s",
                                   (str(handler[0]).split(' '))[2], handler[1],
                                   event, merged_kwargs)

                # call the handler and save the results
                result = handler[0](**merged_kwargs)

                # If whatever handler we called returns False, we stop
                # processing the remaining handlers for boolean or queue events
                if ((ev_type == 'boolean' or ev_type == 'queue') and
                        result is False):

                    # add a False result so our callbacl knows something failed
                    kwargs['ev_result'] = False

                    if self.debug and event != 'timer_tick':
                        self.log.debug("Aborting future event processing")

                    break

                elif ev_type == 'relay' and type(result) is dict:
                    kwargs.update(result)

            self.current_event = None
            self.busy = False
        if self.debug and event != 'timer_tick':
            self.log.debug("vvvv Finished event '%s'. Type: %s. Callback: %s. "
                           "Args: %s", event, ev_type, callback, kwargs)

        # If that event had a callback, let's call it now. We'll also
        # send the result if it's False. Note this means our callback has to
        # expect something.
        # todo is this ok? Should we also pass kwargs?

        # If we had a queue event, we need to see if any handlers asked us to
        # wait for them
        if queue and queue.is_empty():
            self.log.debug("Queue is empty. Deleting.")
            queue = None
            del kwargs['queue']  # ditch this since we don't need it now

        if callback and not queue:

            if result:
                # if our last handler returned something, add it to kwargs
                kwargs['ev_result'] = result

            if kwargs:
                callback(**kwargs)
            else:
                callback()

        # Finally see if we have any more events to process
        self._do_next()

    def _do_next(self):
        # Internal method which checks to see if there are any other events
        # that need to be processed, and then processes them.
        if len(self.queue) > 0:
            event = self.queue.popleft()
            self._process_event(event=event[0],
                                ev_type=event[1],
                                callback=event[2],
                                **event[3])


class QueuedEvent(object):
    """The base class for an event queue which is created each time a queue
    event is called.

    See the documentation at
    http://missionpinball.com/docs/system-components/events/
    for a description of how queue events work.

    """

    def __init__(self, callback, **kwargs):
        self.log = logging.getLogger("Queue")
        self.log.debug("Creating an event queue. Callback: %s Args: %s",
                       callback, kwargs)
        self.callback = callback
        self.kwargs = kwargs
        self.num_waiting = 0

    def wait(self):
        self.num_waiting += 1
        self.log.debug("Registering a wait. Current count: %s",
                       self.num_waiting)

    def clear(self):
        self.num_waiting -= 1
        self.log.debug("Clearing a wait. Current count: %s", self.num_waiting)
        if not self.num_waiting:
            self.log.debug("Queue is empty. Calling %s", self.callback)
            #del self.kwargs['queue']  # ditch this since we don't need it now
            self.callback(**self.kwargs)

    def kill(self):
        # kils this queue without processing the callback
        self.num_waiting = 0

    def is_empty(self):
        if not self.num_waiting:
            return True
        else:
            return False

# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
