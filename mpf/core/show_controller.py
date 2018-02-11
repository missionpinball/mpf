"""Contains the ShowController base class."""

from mpf.assets.show import Show
from mpf.core.mpf_controller import MpfController


class ShowController(MpfController):

    """Manages all the shows in a pinball machine.

    The ShowController handles priorities, restores, running and stopping
    shows, etc.

    """

    config_name = "show_controller"

    def __init__(self, machine):
        """Initialise show controller.

        Args:
            machine: Parent machine object.
        """
        super().__init__(machine)

        self.show_players = {}
        self.running_shows = list()
        self._next_show_id = 0

        # Registers Show with the asset manager
        Show.initialize(self.machine)

        self.machine.events.add_handler('init_phase_3', self._initialize)

        self.machine.mode_controller.register_load_method(
            self._process_config_shows_section, 'shows')

    def _initialize(self, **kwargs):
        del kwargs
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

    def register_show(self, name, settings):
        """Register a named show."""
        if name in self.machine.shows:
            raise ValueError("Show named '{}' was just registered, but "
                             "there's already a show with that name. Shows are"
                             " shared machine-wide".format(name))
        else:
            self.debug_log("Registering show: {}".format(name))
            self.machine.shows[name] = Show(self.machine,
                                            name=name,
                                            data=settings,
                                            file=None)

    def play_show_with_config(self, config, mode=None, start_time=None):
        """Play and return a show from config.

        Will add the mode priority if a mode is passed.
        """
        show = self.machine.shows[config['show']]
        priority = config['priority'] + mode.priority if mode else config['priority']
        running_show = show.play(priority=priority, speed=config['speed'],
                                 start_step=config['start_step'], loops=config['loops'],
                                 sync_ms=config['sync_ms'], manual_advance=config['manual_advance'],
                                 show_tokens=config['show_tokens'], start_time=start_time)

        return running_show
