"""Mode which allows the player to select another mode to run."""
import copy

from mpf.core.utility_functions import Util

from mpf.core.mode import Mode


class Carousel(Mode):

    """Mode which allows the player to select another mode to run."""

    def __init__(self, machine, config, name, path):
        """Initialise carousel mode."""
        self._items = None
        self._select_item_events = None
        self._next_item_events = None
        self._previous_item_events = None
        self._highlighted_item_index = None
        self._done = None
        super().__init__(machine, config, name, path)

    def mode_init(self):
        """Initialise mode and read all settings from config."""
        super().mode_init()
        mode_settings = self.config.get("mode_settings", [])
        self._items = Util.string_to_list(mode_settings.get("selectable_items", ""))
        self._select_item_events = Util.string_to_list(mode_settings.get("select_item_events", ""))
        self._next_item_events = Util.string_to_list(mode_settings.get("next_item_events", ""))
        self._previous_item_events = Util.string_to_list(mode_settings.get("previous_item_events", ""))
        self._highlighted_item_index = 0

        if not self._items:
            raise AssertionError("Specify at least one item to select from")

    def mode_start(self, **kwargs):
        """Start mode and let the player select."""
        super().mode_start(**kwargs)
        self._done = False

        self._register_handlers(self._next_item_events, self._next_item)
        self._register_handlers(self._previous_item_events, self._previous_item)
        self._register_handlers(self._select_item_events, self._select_item)

        player = self.machine.game.player
        if not player.is_player_var('available_items_{}'.format(self.name)):
            player['available_items_{}'.format(self.name)] = copy.deepcopy(self._items)
        self._highlighted_item_index = 0

        self._update_highlighted_item(None)

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
        player = self.machine.game.player
        return player['available_items_{}'.format(self.name)]

    def _next_item(self, **kwargs):
        del kwargs
        if self._done:
            return
        self._highlighted_item_index += 1
        if self._highlighted_item_index >= len(self._get_available_items()):
            self._highlighted_item_index = 0

        self._update_highlighted_item("forwards")

    def _previous_item(self, **kwargs):
        del kwargs
        if self._done:
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
