"""Contains the base classes for the EventManager and QueuedEvents"""
# events.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from collections import deque


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

        Parameters
        ----------

        event : string
            Name of the event you're adding a handler for. Since events are
            text strings, they don't have to be pre-defined.

        handler : string
            The method that will be called when the event is fired.

        priority : int
            An arbitrary integer value that defines what order the handlers
            will be called in. The default is 1, so if you have a handler that
            you want to be called first, add it here with a priority of 2. (Or
            3 or 10 or 100000.) The numbers don't matter. They're called from
            highest to lowest. (i.e. priority 100 is called before priority 1.)

        kwargs : kwargs
            A list of any additional keyword arg pairs that will be attached to
            the handler and called whenever that handler is called. Note these
            are in addition to kwargs that could be passed as part of the
            event post. If there's a conflict, the event-level ones will take
            win.

        Returns
        -------
        handler : object reference
            Returns a reference to the handler which you can use to create a
            list to easily remove these in the future.

        For example:
        ``handler_list.append(events.add_handler('ev', self.test))``

        Then later to remove all the handlers that a module added, you could:
        for handler in handler_list:
        ``events.remove_handler(handler)``

        """
        # Add an entry for this event if it's not there already
        if not event in self.registered_handlers:
            self.registered_handlers[event] = []

        # An event 'handler' in our case is a tuple with three elements:
        # the handler method, the priority, and the dict of kwargs.

        # Check to see if this handler is already registered for this event.
        # If we don't have kwargs, then we'll look for just the handler meth.
        # If we have kwargs, we'll look for that combination

        # If so, remove it
        # We use the slice of the full list [:] to make a copy so we can
        # delete from the original while iterating
        for rh in self.registered_handlers[event][:]:  # rh = registered hndlr
            if rh[0] == handler and rh[2] == kwargs:
                self.registered_handlers[event].remove(rh)

        # Now add it
        self.registered_handlers[event].append((handler, priority, kwargs))
        self.log.debug("Registered %s as a handler for '%s', priority: %s",
                       (str(handler).split(' '))[2], event, priority)

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        self.registered_handlers[event].sort(key=lambda x: x[1], reverse=True)

        return handler

    def remove_handler(self, method, match_kwargs=True, **kwargs):
        """Removes an event handler.

        Args:
            method : The method whose handlers you want to remove.
            match_kwargs: Boolean if False, removes all handlers for that method
                regardless of the kwargs. If True (default) only removes the
                handler if the kwargs you just passed match what's registered.
            **kwargs: The kwargs of the handler you want to remove if
                parameter `match_kwargs` is True
        """

        for event, handler_list in self.registered_handlers.iteritems():
            for handler_tup in handler_list[:]:  # copy via slice
                if handler_tup[0] == method:
                    if not match_kwargs:
                        handler_list.remove(handler_tup)
                        self.log.debug("Removing method %s from event %s",
                                       (str(method).split(' '))[2], event)
                    elif handler_tup[2] == kwargs:
                        handler_list.remove(handler_tup)
                        self.log.debug("Removing method %s from event %s",
                                       (str(method).split(' '))[2], event)

        # If this is the last handler for an event, remove that event
        for k in self.registered_handlers.keys():
            if not self.registered_handlers[k]:  # if value is empty list
                del self.registered_handlers[k]
                self.log.debug("Removing event %s since there are no more"
                               " handlers registered for it", k)

    def does_event_exist(self, event_name):
        """Checks to see if any handlers are registered for the event name that
        is passed.

        Parameters
        ----------

        event_name : str
            The name of the event you want to check

        Returns
        -------

        True or False

        """

        if event_name in self.registered_handlers:
            return True
        else:
            return False

    def post(self, event, **kwargs):
        """Posts an event which causes all the registered handlers to be
        called.

        Events are processed serially (e.g. one at a time), so if the event
        system is in the process of handling another event, this event is
        added to a queue.

        You can specify as many keyword arguments as you want which will be
        pass to each handler. (Just make sure your handlers are expecting them.
        You can add **kwargs to your handler methods if certain ones don't
        need them.

        Args:
            event: A string name of the event you're posting. Note that you can
                post whatever event you want. You don't have to set up anything
                ahead of time, and if no handlers are registered for the event
                you post, so be it.
            ev_type: Optional parameter which specifies the type of event this
                is. Options include 'boolean', 'queue', 'relay', or None. See
                the documentation at https://missionpinball.com/docs for
                details about the different event types.
            callback: A method which will be called when the final handler is
                done processing this event.

        Note that these two special keywords (ev_type and callback) are
        stripped from the list of keyword arguments that are passed to the
        handlers, so you can use them here in your post() without handlers that
        do not expect keywords.

        """
        if self.debug and event != 'timer_tick':
            # Use friendly_kwargs so the logger shows a "friendly" name of the
            # callback handler instead of the bound method object reference.
            friendly_kwargs = dict(kwargs)
            if 'callback' in kwargs:
                friendly_kwargs['callback'] = \
                    (str(kwargs['callback']).split(' '))[2]
            self.log.debug("^^^^ Posted event '%s' with args: %s", event,
                           friendly_kwargs)
        if not self.busy:
            self._do_event(event, **kwargs)
        else:

            self.log.debug("XXXX Event '%s' is in progress. Added to the "
                           "queue.", self.current_event)
            self.queue.append((event, kwargs))

    def _do_event(self, event, **kwargs):
        # Internal method which actually handles the events. Don't call this.
        callback = None
        ev_type = None
        result = None
        queue = None
        if self.debug and event != 'timer_tick':
            # Show friendly callback name. See comment in post() above.
            friendly_kwargs = dict(kwargs)
            if 'callback' in kwargs:
                friendly_kwargs['callback'] = \
                    (str(kwargs['callback']).split(' '))[2]
            self.log.debug("^^^^ Processing event '%s' with args: %s", event,
                           friendly_kwargs)

        # if our kwargs include ev_type or callback, we want to pull them
        # out of the kwargs we send to all the registered handlers:
        if 'ev_type' in kwargs:
            ev_type = kwargs['ev_type']
            del kwargs['ev_type']

        if 'callback' in kwargs:
            callback = kwargs['callback']
            del kwargs['callback']

        # Now let's call the handlers one-by-one, including any remaining
        # kwargs
        if event in self.registered_handlers:
            self.busy = True
            self.current_event = event

            if ev_type == 'queue' and callback:
                queue = QueuedEvent(callback, **kwargs)
                kwargs['queue'] = queue

            for handler in self.registered_handlers[event][:]:

                # use slice above so we don't process new handlers that came
                # in while we were processing previous handlers

                # merge the posts kwargs with the registered handler's kwargs
                # in case of conflict, posts kwargs will win
                merged_kwargs = dict(handler[2].items() + kwargs.items())

                # log if debug is enabled and this event is not the timer tick
                if self.debug and event != 'timer_tick':
                    self.log.debug("%s responding to event '%s' with args %s",
                                   (str(handler[0]).split(' '))[2], event,
                                   kwargs)

                # call the handler and save the results
                result = handler[0](**merged_kwargs)

                # If whatever handler we called returns False, we stop
                # processing the remaining handlers for bool or queue events
                if (ev_type == 'boolean' or ev_type == 'queue') and \
                        result is False:

                    # add a False result so our handlers no something failed
                    kwargs['ev_result'] = False

                    if self.debug and event != 'timer_tick':
                        self.log.debug("Aborting future event processing")

                    break

                elif ev_type == 'relay':
                    kwargs = result

            self.current_event = None
            self.busy = False
        if self.debug and event != 'timer_tick':
            self.log.debug("vvvv Finished event '%s' with args: %s",
                           event, kwargs)

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

        if callback:
            if not queue:
                # if we have a queue kwarg from before, strip it since we only
                # needed it to setup the queue
                if kwargs and 'queue' in kwargs:
                    del kwargs['queue']

                if result:
                    # if our last handler returned something, add it to kwargs
                    kwargs['ev_result'] = result

                callback(**kwargs)

        # Finally see if we have any more events to process
        self._do_next()

    def _do_next(self):
        # Internal method which checks to see if there are any other events
        # that need to be processed, and then processes them.
        if len(self.queue) > 0:
            event = self.queue.popleft()
            self._do_event(event[0], **event[1])


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

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
