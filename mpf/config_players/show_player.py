"""Show config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class ShowPlayer(DeviceConfigPlayer):

    """Plays, starts, stops, pauses, resumes or advances shows based on config."""

    config_file_section = 'show_player'
    show_section = 'shows'
    allow_placeholders_in_keys = True

    __slots__ = []

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Play, start, stop, pause, resume or advance show based on config."""
        # make sure all shows play in sync
        queue = kwargs.get("queue", None)
        start_time = kwargs.get("start_time", None)
        if not start_time:
            start_time = self.machine.clock.get_time()
        for show, show_settings in settings.items():
            # Look for a conditional event in the show name
            show_dict = self.machine.placeholder_manager.parse_conditional_template(show)
            if show_dict['condition'] and not show_dict['condition'].evaluate(kwargs):
                continue

            show_settings = dict(show_settings)
            if 'hold' in show_settings and show_settings['hold'] is not None:
                raise AssertionError(
                    "Setting 'hold' is no longer supported for shows. Use duration -1 in your show.")
            try:
                show_settings['priority'] += priority
            except KeyError:
                show_settings['priority'] = priority
            # todo need to add this key back to the config player

            self._update_show(show_dict["name"], show_settings, context, queue, start_time, kwargs)

    def handle_subscription_change(self, value, settings, priority, context):
        """Handle subscriptions."""
        instance_dict = self._get_instance_dict(context)
        for show, show_settings in settings.items():
            show_settings = dict(show_settings)
            if show_settings['action'] != 'play':
                raise AssertionError("Can only use action play with subscriptions.")

            if 'key' in show_settings and show_settings['key']:
                key = show_settings['key']
            else:
                key = show

            if value:
                self._play(key, instance_dict, show, show_settings, False, None, {})
            else:
                self._stop(key, instance_dict, show, show_settings, False, None, {})

    # pylint: disable-msg=too-many-arguments
    def _play(self, key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        stop_callback = None
        if show_settings['block_queue']:
            if not queue:
                raise AssertionError("block_queue can only be used with a queue event.")
            queue.wait()
            stop_callback = queue.clear

        start_step = show_settings['start_step'].evaluate(placeholder_args)

        show_config = self.machine.show_controller.create_show_config(
            show, show_settings['priority'], show_settings['speed'], show_settings['loops'], show_settings['sync_ms'],
            show_settings['manual_advance'], show_settings['show_tokens'], show_settings['events_when_played'],
            show_settings['events_when_stopped'], show_settings['events_when_looped'],
            show_settings['events_when_paused'], show_settings['events_when_resumed'],
            show_settings['events_when_advanced'], show_settings['events_when_stepped_back'],
            show_settings['events_when_updated'], show_settings['events_when_completed'])

        previous_show = instance_dict.get(key, None)

        instance_dict[key] = self.machine.show_controller.replace_or_advance_show(previous_show, show_config,
                                                                                  start_step, start_time, stop_callback)

    @staticmethod
    def _stop(key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del show
        del show_settings
        del queue
        del start_time
        del placeholder_args
        if key in instance_dict:
            instance_dict[key].stop()
            del instance_dict[key]

    @staticmethod
    def _pause(key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del show
        del show_settings
        del queue
        del start_time
        del placeholder_args
        if key in instance_dict:
            instance_dict[key].pause()

    @staticmethod
    def _resume(key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del show
        del show_settings
        del queue
        del start_time
        del placeholder_args
        if key in instance_dict:
            instance_dict[key].resume()

    @staticmethod
    def _advance(key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del show
        del show_settings
        del queue
        del start_time
        del placeholder_args
        if key in instance_dict:
            instance_dict[key].advance()

    @staticmethod
    def _step_back(key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del show
        del show_settings
        del queue
        del start_time
        del placeholder_args
        if key in instance_dict:
            instance_dict[key].step_back()

    @staticmethod
    def _update(key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del show
        del queue
        del start_time
        del placeholder_args
        if key in instance_dict:
            instance_dict[key].update(
                show_tokens=show_settings['show_tokens'],
                priority=show_settings['priority'])

    # pylint: disable-msg=too-many-arguments
    def _update_show(self, show, show_settings, context, queue, start_time, placeholder_args):
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

        action = actions.get(show_settings['action'], None)

        if not callable(action):
            raise AssertionError("Invalid action {} in show_player {}".format(
                show_settings['action'], key))

        if 'show' in show_settings and show_settings['show']:
            show_name = show_settings['show']
        else:
            show_name = show

        action(key, instance_dict, show_name, show_settings, queue, start_time, placeholder_args)

    def clear_context(self, context):
        """Stop running shows from context."""
        for show in self._get_instance_dict(context).values():
            show.stop()
        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        return {"action": value}
