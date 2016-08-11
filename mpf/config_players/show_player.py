"""Show config player."""
from copy import deepcopy

from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):

    """Plays, starts, stops, pauses, resumes or advances shows based on config."""

    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    def play(self, settings, context, priority=0, **kwargs):
        """Play, start, stop, pause, resume or advance show based on config."""
        if 'shows' in settings:
            settings = settings['shows']

        settings = deepcopy(settings)

        # show_tokens = kwargs.get('show_tokens', None)

        for show, s in settings.items():
            if 'hold' in s and s['hold'] is not None:
                raise AssertionError("Setting 'hold' is no longer supported for shows. Use duration -1 in your show.")
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            # todo need to add this key back to the config player

            self._update_show(show, s, context)

    def _update_show(self, show, s, context):
        instance_dict = self._get_instance_dict(context)
        if 'key' in s and s['key']:
            key = s['key']
        else:
            key = show

        if s['action'].lower() == 'play':
            if key in instance_dict:
                instance_dict[key].stop()
            try:
                show_instance = self.machine.shows[show].play(
                    show_tokens=s['show_tokens'],
                    priority=s['priority'],
                    speed=s['speed'],
                    start_step=s['start_step'],
                    loops=s['loops'],
                    sync_ms=s['sync_ms'],
                    reset=s['reset'],
                    manual_advance=s['manual_advance'],
                )
                instance_dict[key] = show_instance
            except KeyError:
                raise KeyError("Cannot play show '{}'. No show with that "
                               "name.".format(show))

        elif s['action'].lower() == 'stop':
            if key in instance_dict:
                instance_dict[key].stop()
                del instance_dict[key]

        elif s['action'].lower() == 'pause':
            if key in instance_dict:
                instance_dict[key].pause()

        elif s['action'].lower() == 'resume':
            if key in instance_dict:
                instance_dict[key].resume()

        elif s['action'].lower() == 'advance':
            if key in instance_dict:
                instance_dict[key].advance()

        elif s['action'].lower() == 'update':
            if key in instance_dict:
                instance_dict[key].update(
                    show_tokens=s['show_tokens'],
                    priority=s['priority'])

    def clear_context(self, context):
        """Stop running shows from context."""
        for show in self._get_instance_dict(context).values():
            show.stop()
        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        return {"action": value}

player_cls = ShowPlayer
