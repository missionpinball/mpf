"""Show config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class ShowPlayer(DeviceConfigPlayer):

    """Plays, starts, stops, pauses, resumes or advances shows based on config."""

    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, context, calling_context, priority=0, queue=None, **kwargs):
        """Play, start, stop, pause, resume or advance show based on config."""
        for show, show_settings in settings.items():
            show_settings = dict(show_settings)
            if 'hold' in show_settings and show_settings['hold'] is not None:
                raise AssertionError("Setting 'hold' is no longer supported for shows. Use duration -1 in your show.")
            try:
                show_settings['priority'] += priority
            except KeyError:
                show_settings['priority'] = priority

            # todo need to add this key back to the config player

            self._update_show(show, show_settings, context, queue)

    # pylint: disable-msg=too-many-arguments
    def _play(self, key, instance_dict, show, show_settings, queue):
        callback = None
        if show_settings['block_queue']:
            if not queue:
                raise AssertionError("block_queue can only be used with a queue event.")
            queue.wait()
            callback = queue.clear

        if key in instance_dict:
            instance_dict[key].stop()
        try:
            show_instance = self.machine.shows[show].play(
                show_tokens=show_settings['show_tokens'],
                priority=show_settings['priority'],
                speed=show_settings['speed'],
                start_step=show_settings['start_step'].evaluate({}),
                loops=show_settings['loops'],
                sync_ms=show_settings['sync_ms'],
                manual_advance=show_settings['manual_advance'],
                callback=callback,
                events_when_played=show_settings['events_when_played'],
                events_when_stopped=show_settings['events_when_stopped'],
                events_when_looped=show_settings['events_when_looped'],
                events_when_paused=show_settings['events_when_paused'],
                events_when_resumed=show_settings['events_when_resumed'],
                events_when_advanced=show_settings['events_when_advanced'],
                events_when_stepped_back=show_settings[
                    'events_when_stepped_back'],
                events_when_updated=show_settings['events_when_updated'],
                events_when_completed=show_settings['events_when_completed']
            )
            instance_dict[key] = show_instance
        except KeyError:
            raise KeyError("Cannot play show '{}'. No show with that "
                           "name.".format(show))

    @staticmethod
    def _stop(key, instance_dict, show, show_settings, queue):
        del show
        del show_settings
        del queue
        if key in instance_dict:
            instance_dict[key].stop()
            del instance_dict[key]

    @staticmethod
    def _pause(key, instance_dict, show, show_settings, queue):
        del show
        del show_settings
        del queue
        if key in instance_dict:
            instance_dict[key].pause()

    @staticmethod
    def _resume(key, instance_dict, show, show_settings, queue):
        del show
        del show_settings
        del queue
        if key in instance_dict:
            instance_dict[key].resume()

    @staticmethod
    def _advance(key, instance_dict, show, show_settings, queue):
        del show
        del show_settings
        del queue
        if key in instance_dict:
            instance_dict[key].advance()

    @staticmethod
    def _step_back(key, instance_dict, show, show_settings, queue):
        del show
        del show_settings
        del queue
        if key in instance_dict:
            instance_dict[key].step_back()

    @staticmethod
    def _update(key, instance_dict, show, show_settings, queue):
        del show
        del queue
        if key in instance_dict:
            instance_dict[key].update(
                show_tokens=show_settings['show_tokens'],
                priority=show_settings['priority'])

    def _update_show(self, show, show_settings, context, queue):
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

        action(key, instance_dict, show, show_settings, queue)

    def clear_context(self, context):
        """Stop running shows from context."""
        for show in self._get_instance_dict(context).values():
            show.stop()
        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        return {"action": value}

player_cls = ShowPlayer
