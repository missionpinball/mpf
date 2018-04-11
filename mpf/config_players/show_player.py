"""Show config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class ShowPlayer(DeviceConfigPlayer):

    """Plays, starts, stops, pauses, resumes or advances shows based on config."""

    config_file_section = 'show_player'
    show_section = 'shows'

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
        callback = None
        if show_settings['block_queue']:
            if not queue:
                raise AssertionError("block_queue can only be used with a queue event.")
            queue.wait()
            callback = queue.clear

        start_step = show_settings['start_step'].evaluate(placeholder_args)

        if key in instance_dict and not instance_dict[key].stopped:
            # this is an optimization for the case where we only advance a show or do not change it at all
            # pylint: disable-msg=too-many-boolean-expressions
            if (show == instance_dict[key].show.name and
                    instance_dict[key].show_tokens == show_settings['show_tokens'] and
                    instance_dict[key].priority == show_settings['priority'] and
                    instance_dict[key].speed == show_settings['speed'] and
                    instance_dict[key].loops == show_settings['loops'] and
                    instance_dict[key].sync_ms == (show_settings['sync_ms'] if show_settings['sync_ms'] else 0) and
                    instance_dict[key].manual_advance == show_settings['manual_advance'] and
                    not callback and not show_settings['events_when_played'] and
                    not show_settings['events_when_played'] and not instance_dict[key].events["play"] and
                    not show_settings['events_when_stopped'] and not instance_dict[key].events["stop"] and
                    instance_dict[key].events["loop"] == show_settings['events_when_looped'] and
                    instance_dict[key].events["pause"] == show_settings['events_when_paused'] and
                    instance_dict[key].events["resume"] == show_settings['events_when_resumed'] and
                    instance_dict[key].events["advance"] == show_settings['events_when_advanced'] and
                    instance_dict[key].events["step_back"] == show_settings['events_when_stepped_back'] and
                    instance_dict[key].events["update"] == show_settings['events_when_updated'] and
                    instance_dict[key].events["complete"] == show_settings['events_when_completed']):
                if instance_dict[key].current_step_index is not None and \
                        instance_dict[key].current_step_index + 1 == start_step:
                    # the show already is at the target step
                    return
                elif instance_dict[key].current_step_index is not None and \
                        instance_dict[key].current_step_index + 2 == start_step:
                    # advance show to target step
                    instance_dict[key].advance()
                    return
            # in all other cases stop the current show
            instance_dict[key].stop()
        try:
            show_obj = self.machine.shows[show]
        except KeyError:
            raise KeyError("Cannot play show '{}'. No show with that "
                           "name.".format(show))

        instance_dict[key] = show_obj.play(
            show_tokens=show_settings['show_tokens'],
            priority=show_settings['priority'],
            speed=show_settings['speed'],
            start_time=start_time,
            start_step=start_step,
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

        action = actions.get(show_settings['action'].lower(), None)

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
