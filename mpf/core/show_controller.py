"""Contains the ShowController base class."""

import logging

from mpf.assets.show import Show


class ShowController(object):

    """Manages all the shows in a pinball machine.

    'hardware shows' are coordinated light, flasher, coil, and event effects.
    The ShowController handles priorities, restores, running and stopping
    Shows, etc. There should be only one per machine.

    Args:
        machine: Parent machine object.
    """

    def __init__(self, machine):
        """Initialise show controller."""
        self.log = logging.getLogger("ShowController")
        self.machine = machine

        self.show_players = {}
        self.running_shows = list()
        self._next_show_id = 0

        # Registers Show with the asset manager
        Show.initialize(self.machine)

        self.machine.events.add_handler('init_phase_3', self._initialize)

        self.machine.mode_controller.register_load_method(
            self._process_config_shows_section, 'shows')

    def _initialize(self):
        if 'shows' in self.machine.config:
            self._process_config_shows_section(self.machine.config['shows'])

    def get_next_show_id(self):
        """Return the next show id."""
        self._next_show_id += 1
        return self._next_show_id

    def _process_config_shows_section(self, config, **kwargs):
        # processes the shows: section of a mode or machine config
        del kwargs

        for show, settings in config.items():
            self.register_show(show, settings)

    def get_running_shows(self, name):
        """Return a list of running shows by show name or instance name.

        Args:
            name: String name of the running shows you want to get. This can
                be a show name (which will return all running instances of that
                show) or a key (which will also return all running
                show instances that have that instance name).

        Returns:
            A list of RunningShow() objects.

        """
        return [x for x in self.running_shows if x.name == name]

    def register_show(self, name, settings):
        """Register a named show."""
        if name in self.machine.shows:
            raise ValueError("Show named '{}' was just registered, but "
                             "there's already a show with that name. Shows are"
                             " shared machine-wide".format(name))
        else:
            self.machine.shows[name] = Show(self.machine,
                                            name=name,
                                            data=settings,
                                            file=None)

    def notify_show_starting(self, show):
        """Register a running show."""
        self.running_shows.append(show)
        self.running_shows.sort(key=lambda x: x.priority)

    def notify_show_stopping(self, show):
        """Remove a running show."""
        self.running_shows.remove(show)
