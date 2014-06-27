import logging
from collections import deque


class EventManager(object):

    def __init__(self):
        self.log = logging.getLogger("Events")
        self.event_queue = []
        self.registered_handlers = {}
        self.busy = False
        self.queue = deque([])
        self.current_event = None
        self.debug = True  # logs all event activity except timer_ticks.

    def add_handler(self, event, handler, priority=1):
        """ Registers an event handler to respond to an event. 

        Parameters:

        event - string name for an event. Since events are text strings, they
        don't have to be pre-defined.

        handler - a method that will be called when the event is fired.

        priority - an arbitrary integer value that defines what order the
        handlers will be called. The default is 1, so if you have a handler
        that you want to be called first, add it here with a priority of 2. (Or
        3 or 10 or 100000. The numbers don't matter. They're called from
        highest to lowest. (i.e. priority 100 is called before priority 1.)

        Note if you add a handlers for an event that has already been
        registered, the new one will overwrite the old one. This is useful for
        changing priorities of existing handlers. Also it's good to know that
        you can safely add a handler over and over.

        Returns a reference to the handler which you can use to create a list
        to easily remove these in the future.

        For example, handler_list.append(events.add_handler('ev', self.test))

        Then later to remove all the handlers that a module added, you could:
        for handler in handler_list:
            events.remove_handler(handler)
        """
        # Add an entry for this event if it's not there already
        if not event in self.registered_handlers:
            self.registered_handlers[event] = []

        # Check to see if this handler is already registered for this event.
        # If so, remove it
        # We use the slice of the full list [:] to make a copy so we can
        # delete from the original while iterating
        for rh in self.registered_handlers[event][:]:
            if rh[0] == handler:
                self.registered_handlers[event].remove(rh)

        # Now add it
        self.registered_handlers[event].append((handler, priority))
        self.log.debug("Registered %s...", handler)
        self.log.debug("...as a handler for '%s', priority: %s", event,
                       priority)

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        self.registered_handlers[event].sort(key=lambda x: x[1], reverse=True)

        return handler

    def remove_handler(self, method):
        """Removes an event handler.

        Parameters:

        method - this is the method whose handlers you want to remove. This
        removes all of them. todo for the future: specify a method / event
        combo?
        """
        for event, handler_list in self.registered_handlers.iteritems():
            for handler_tup in handler_list[:]:
                if handler_tup[0] == method:
                    handler_list.remove(handler_tup)
                    self.log.debug("Removing method %s from event %s",
                                   method, event)

        # If this is the last handler for an event, remove that event
        for k in self.registered_handlers:
            if len(k) == 0:
                del self.registered_handlers[k]
                self.log.debug("Removing event %s since there are no more"
                               " handlers registered for it", k)

    def post(self, event, **kwargs):
        """ Posts an event which causes all the registered handlers to be
        called. Only one event can be 'active' at a time, so if the event
        system is in the process of handling another event, this event is
        added to a queue.

        You can specify as many keyword arguments as you want which will be
        pass to each handler. (Just make sure your handlers are expecting them.
        You can add **kwargs to your handler methods if certain ones don't
        need them.

        There are a few special parameters you can also pass here. (Should I
        add these to the def statement above? Am I breaking pythonic rules
        by not??

        Special keyword arguments include:

        ev_type - if you specify "boolean" as an event type (by passing
        ev_type='boolean') then this event will stop processing if any
        handlers return False. Otherwise handlers that return False will have
        no effect

        callback - this is a method that will be called after the last handler
        is done

        Note that these two special keywords (ev_type and callback) are
        stripped from the list of keyword arguments that are passed to the
        handlers. So you can use them here in your post() without handlers that
        do not expect keywords.
        """
        if self.debug and event != 'timer_tick':
            self.log.debug("^^^^ Posted event '%s' with args: %s", event,
                           kwargs)
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
            self.log.debug(">>>> Processing event '%s' Args: %s",
                           event, kwargs)

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

            for handler in self.registered_handlers[event]:
                if self.debug and event != 'timer_tick':
                    self.log.debug("Event handler responding: %s to "
                                   "event '%s', with args %s", handler[0],
                                   event, kwargs)
                result = handler[0](**kwargs)
                # If whatever method we called returns False, we stop
                # processing the remaining handlers
                if (ev_type == 'boolean' or ev_type == 'queue') and \
                        result is False:
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

        if callback and not queue:
            # if we have a queue kwarg from before, strip it since we only
            # needed it to setup the queue
            if 'queue' in kwargs:
                del kwargs['queue']

            # If we have a result, we pass it as a kwarg
            # This is the result of the last handler processed
            if result is not None:
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
    """ This queue fills up and then empties. When it's all empty it does
    the callback.
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
            self.callback(**self.kwargs)

    def kill(self):
        # kils this queue without processing the callback
        self.num_waiting = 0

    def is_empty(self):
        if not self.num_waiting:
            return True
        else:
            return False

