"""Mode which allows the player to select another mode to run."""
from mpf.core.utility_functions import Util

from mpf.core.mode import Mode


class Carousel(Mode):

    """Mode which allows the player to select another mode to run."""

    __slots__ = ["_all_items", "_items", "_select_item_events", "_next_item_events",
                 "_previous_item_events", "_highlighted_item_index", "_done",
                 "_block_events", "_release_events", "_is_blocking"]

    def __init__(self, *args, **kwargs):
        """Initialise carousel mode."""
        self._all_items = None
        self._items = None
        self._select_item_events = None
        self._next_item_events = None
        self._previous_item_events = None
        self._highlighted_item_index = None
        self._block_events = None
        self._release_events = None
        self._is_blocking = None
        self._done = None
        super().__init__(*args, **kwargs)

    def mode_init(self):
        """Initialise mode and read all settings from config."""
        super().mode_init()
        mode_settings = self.config.get("mode_settings", [])
        self._all_items = []
        for item in Util.string_to_event_list(mode_settings.get("selectable_items", "")):
            placeholder = self.machine.placeholder_manager.parse_conditional_template(item)
            # Only add a placeholder if there's a condition, otherwise just the string
            self._all_items.append(placeholder if placeholder.condition else item)
        self._select_item_events = Util.string_to_event_list(mode_settings.get("select_item_events", ""))
        self._next_item_events = Util.string_to_event_list(mode_settings.get("next_item_events", ""))
        self._previous_item_events = Util.string_to_event_list(mode_settings.get("previous_item_events", ""))
        self._highlighted_item_index = 0
        self._block_events = Util.string_to_event_list(mode_settings.get("block_events", ""))
        self._release_events = Util.string_to_event_list(mode_settings.get("release_events", ""))

        if not self._all_items:
            raise AssertionError("Specify at least one item to select from")

    def mode_start(self, **kwargs):
        """Start mode and let the player select."""
        self._items = []
        for item in self._all_items:
            # All strings go in, but only conditional templates if they evaluate true
            if isinstance(item, str):
                self._items.append(item)
            elif not item.condition or item.condition.evaluate({}):
                self._items.append(item.name)
        if not self._items:
            self.machine.events.post("{}_items_empty".format(self.name))
            '''event (carousel_name)_items_empty
                desc: A carousel's items are all conditional and all evaluated false.
                    If this event is posted, the carousel mode will not be started.
                '''
            self.stop()
            return

        super().mode_start(**kwargs)
        self._done = False
        self._is_blocking = False

        self._register_handlers(self._next_item_events, self._next_item)
        self._register_handlers(self._previous_item_events, self._previous_item)
        self._register_handlers(self._select_item_events, self._select_item)

        self._highlighted_item_index = 0
        self._update_highlighted_item(None)

        # If set to block next/prev on flipper cancel, set those event handlers
        if self._block_events:
            # This rudimentary implementation will block on any block_event
            # and release on any release_event. If future requirements need to
            # track *which* block_event blocked and *only* release on the
            # corresponding release_event, additional work will be needed.
            for event in self._block_events:
                self.add_mode_event_handler(event, self._block_enable, priority=100)
            for event in self._release_events:
                self.add_mode_event_handler(event, self._block_disable, priority=100)

    def _register_handlers(self, events, handler):
        for event in events:
            self.add_mode_event_handler(event, handler)

    def _get_highlighted_item(self):
        return self._get_available_items()[self._highlighted_item_index]

    def _update_highlighted_item(self, direction):
        self.debug_log("Highlighted item: " + self._get_highlighted_item())

        self.machine.events.post("{}_{}_highlighted".format(self.name, self._get_highlighted_item()),
                                 direction=direction)
        '''event (carousel_name)_(item)_highlighted
            desc: Player highlighted an item in a carousel. Mostly used to play shows or trigger slides.
            args:
               direction: The direction the carousel is moving. Either forwards or backwards. None on mode start.
            '''

    def _get_available_items(self):
        # Return the default items
        return self._items

    def _next_item(self, **kwargs):
        del kwargs
        if self._done or self._is_blocking:
            return
        self._highlighted_item_index += 1
        if self._highlighted_item_index >= len(self._get_available_items()):
            self._highlighted_item_index = 0
        self._update_highlighted_item("forwards")

    def _previous_item(self, **kwargs):
        del kwargs
        if self._done or self._is_blocking:
            return
        self._highlighted_item_index -= 1
        if self._highlighted_item_index < 0:
            self._highlighted_item_index = len(self._get_available_items()) - 1

        self._update_highlighted_item("backwards")

    def _select_item(self, **kwargs):
        del kwargs
        if self._done:
            return
        self.debug_log("Selected mode: " + str(self._get_highlighted_item()))
        self._done = True

        self.machine.events.post("{}_{}_selected".format(self.name, self._get_highlighted_item()))
        '''event (carousel_name)_(item)_selected
            desc: Player selected an item in a carousel. Can be used to trigger modes. '''
        self.machine.events.post("{}_item_selected".format(self.name))
        '''event (carousel_name)_item_selected
            desc: Player selected any item in a carousel. Used to stop mode. '''

    def _block_enable(self, **kwargs):
        del kwargs
        self._is_blocking = True

    def _block_disable(self, **kwargs):
        del kwargs
        self._is_blocking = False
