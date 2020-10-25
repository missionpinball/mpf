"""Random event config player."""
from mpf.core.config_player import ConfigPlayer
from mpf.core.randomizer import Randomizer
from mpf.core.utility_functions import Util


class RandomEventPlayer(ConfigPlayer):

    """Plays a random event based on config."""

    config_file_section = 'random_event_player'
    show_section = 'random_events'

    __slots__ = ["_machine_wide_dict"]

    def __init__(self, machine):
        """Initialise random event player."""
        super().__init__(machine)
        self._machine_wide_dict = {}

    @staticmethod
    def is_entry_valid_outside_mode(settings) -> bool:
        """Return true if scope is not player."""
        return settings['scope'] != "player"

    def _get_randomizer(self, settings, context, calling_context):
        key = "random_{}.{}".format(context, calling_context)
        if settings['scope'] == "player":
            if not self.machine.game.player[key]:
                self.machine.game.player[key] = Randomizer(
                    settings['events'], self.machine, template_type="event")
                r'''player_var: random_(x).(y)

                desc: Holds references to Randomizer settings that need to be
                tracked on a player basis. There is nothing you need to know
                or do with this, rather this is just FYI on what the player
                variables that start with "random\_" are.
                '''

                if settings['force_all']:
                    self.machine.game.player[key].force_all = True

                if not settings['force_different']:
                    self.machine.game.player[key].force_different = False

                if settings['disable_random']:
                    self.machine.game.player[key].disable_random = True

                self.machine.game.player[key].fallback_value = settings.get('fallback_event')

            return self.machine.game.player[key]

        if key not in self._machine_wide_dict:
            self._machine_wide_dict[key] = Randomizer(
                settings['events'], self.machine, template_type="event")

            if settings['force_all']:
                self._machine_wide_dict[key].force_all = True

            if not settings['force_different']:
                self._machine_wide_dict[key].force_different = False

            if settings['disable_random']:
                self._machine_wide_dict[key].disable_random = True

            self._machine_wide_dict[key].fallback_value = settings.get('fallback_event')

        return self._machine_wide_dict[key]

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Play a random event from list based on config."""
        del priority
        randomizer = self._get_randomizer(settings, context, calling_context)
        # With conditional events in randomizer, there may not be a next event
        next_event = randomizer.get_next(kwargs)
        if next_event:
            self.machine.events.post(next_event, **kwargs)

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        config = self._parse_config(settings, name)
        return config

    def get_express_config(self, value):
        """Parse express config."""
        return {"events": self.get_list_config(Util.string_to_event_list(value))}

    def get_list_config(self, value):
        """Parse list."""
        return {"events": value}
