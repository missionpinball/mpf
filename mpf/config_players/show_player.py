"""Show config player."""
from copy import deepcopy

from mpf.config_players.device_config_player import DeviceConfigPlayer


class ShowPlayer(DeviceConfigPlayer):

    """Plays, starts, stops, pauses, resumes or advances shows based on config."""

    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    def play(self, settings, context, priority=0, **kwargs):
        """Play, start, stop, pause, resume or advance show based on config."""
        settings = deepcopy(settings)

        # show_tokens = kwargs.get('show_tokens', None)

        for show, show_settings in settings.items():
            if 'hold' in show_settings and show_settings['hold'] is not None:
                raise AssertionError("Setting 'hold' is no longer supported for shows. Use duration -1 in your show.")
            try:
                show_settings['priority'] += priority
            except KeyError:
                show_settings['priority'] = priority

            # todo need to add this key back to the config player

            self._update_show(show, show_settings, context)

    def _play(self, key, instance_dict, show, show_settings):
        if key in instance_dict:
            instance_dict[key].stop()
        try:
            show_instance = self.machine.shows[show].play(
                show_tokens=show_settings['show_tokens'],
                priority=show_settings['priority'],
                speed=show_settings['speed'],
                start_step=show_settings['start_step'],
                loops=show_settings['loops'],
                sync_ms=show_settings['sync_ms'],
                manual_advance=show_settings['manual_advance'],
            )
            instance_dict[key] = show_instance
        except KeyError:
            raise KeyError("Cannot play show '{}'. No show with that "
                           "name.".format(show))

    @staticmethod
    def _stop(key, instance_dict, show, show_settings):
        del show
        del show_settings
        if key in instance_dict:
            instance_dict[key].stop()
            del instance_dict[key]

    @staticmethod
    def _pause(key, instance_dict, show, show_settings):
        del show
        del show_settings
        if key in instance_dict:
            instance_dict[key].pause()

    @staticmethod
    def _resume(key, instance_dict, show, show_settings):
        del show
        del show_settings
        if key in instance_dict:
            instance_dict[key].resume()

    @staticmethod
    def _advance(key, instance_dict, show, show_settings):
        del show
        del show_settings
        if key in instance_dict:
            instance_dict[key].advance()

    @staticmethod
    def _step_back(key, instance_dict, show, show_settings):
        del show
        del show_settings
        if key in instance_dict:
            instance_dict[key].step_back()

    @staticmethod
    def _update(key, instance_dict, show, show_settings):
        del show
        if key in instance_dict:
            instance_dict[key].update(
                show_tokens=show_settings['show_tokens'],
                priority=show_settings['priority'])

    def _update_show(self, show, show_settings, context):
        instance_dict = self._get_instance_dict(context)
        if 'key' in show_settings and show_settings['key']:
            key = show_settings['key']
        else:
            key = show

        actions = {
            'play': self._play,
            'stop': self._stop,
            'pause': self._pause,
            'resume': self._resume,
            'advance': self._advance,
            'step_back': self._step_back,
            'update': self._update
        }

        action = actions.get(show_settings['action'].lower(), None)

        if not callable(action):
            raise AssertionError("Invalid action {} in show_player {}".format(show_settings['action'], key))

        action(key, instance_dict, show, show_settings)

    def clear_context(self, context):
        """Stop running shows from context."""
        for show in self._get_instance_dict(context).values():
            show.stop()
        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        return {"action": value}

player_cls = ShowPlayer
