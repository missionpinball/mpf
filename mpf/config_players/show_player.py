"""Show config player."""
from mpf.core.placeholder_manager import ConditionalEvent

from mpf.config_players.device_config_player import DeviceConfigPlayer

RESERVED_KEYS = ["show", "priority", "speed", "block_queue", "start_step", "loops", "sync_ms", "manual_advance",
                 "key", "show_tokens", "events_when_played", "events_when_stopped", "events_when_looped",
                 "events_when_paused", "events_when_resumed", "events_when_advanced",
                 "events_when_stepped_back", "events_when_updated", "events_when_completed"]


class ShowPlayer(DeviceConfigPlayer):

    """Plays, starts, stops, pauses, resumes or advances shows based on config."""

    config_file_section = 'show_player'
    show_section = 'shows'
    allow_placeholders_in_keys = True

    __slots__ = ["_actions"]

    def __init__(self, machine):
        """Initialise show player."""
        super().__init__(machine)
        self._actions = {
            'play': self._play,
            'stop': self._stop,
            'pause': self._pause,
            'resume': self._resume,
            'advance': self._advance,
            'step_back': self._step_back,
            'update': self._update,
            'queue': self._queue
        }

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Play, start, stop, pause, resume or advance show based on config."""
        # make sure all shows play in sync
        queue = kwargs.get("queue", None)
        start_time = kwargs.get("start_time", None)
        show_tokens = kwargs.get("show_tokens", kwargs)
        if not start_time:
            start_time = self.machine.clock.get_time()
        for show, show_settings in settings.items():
            # Look for a conditional event in the show name
            if show.condition and not show.condition.evaluate(kwargs):
                continue

            if 'hold' in show_settings and show_settings['hold'] is not None:
                raise AssertionError(
                    "Setting 'hold' is no longer supported for shows. Use duration -1 in your show.")
            if priority:
                show_settings = dict(show_settings)
                try:
                    show_settings['priority'] += priority
                except KeyError:
                    show_settings['priority'] = priority

            self._update_show(show.name, show_settings, context, queue, start_time, show_tokens)

    def _expand_device(self, device):
        # parse conditionals
        devices = super()._expand_device(device)
        for index, device_entry in enumerate(devices):
            if not isinstance(device_entry, ConditionalEvent):
                devices[index] = self.machine.placeholder_manager.parse_conditional_template(device_entry)
        return devices

    def _expand_device_config(self, device_settings):
        """Validate show_tokens."""
        for key in RESERVED_KEYS:
            if key in device_settings["show_tokens"]:
                self.raise_config_error("Key {} is not allowed in show_tokens of your show_player because it is also "
                                        "an option in show_player. Did you indent that option too far?".format(key), 1)
        return device_settings

    def handle_subscription_change(self, value, settings, priority, context, key):
        """Handle subscriptions."""
        instance_dict = self._get_instance_dict(context)
        for show, show_settings in settings.items():
            show_settings = dict(show_settings)

            show_key = show_settings["key"] if 'key' in show_settings and show_settings['key'] else key

            if show_settings['action'] != 'play':
                raise AssertionError("Can only use action play with subscriptions.")

            if value:
                self._play(show_key, instance_dict, show.name, show_settings, False, None, {})
            else:
                self._stop(show_key, instance_dict, show.name, show_settings, False, None, {})

    # pylint: disable-msg=too-many-arguments
    def _play(self, key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        stop_callback = None
        if show_settings['block_queue']:
            if not queue:
                raise AssertionError("block_queue can only be used with a queue event.")
            queue.wait()
            stop_callback = queue.clear
        start_step = show_settings['start_step'].evaluate(placeholder_args)
        start_running = show_settings['start_running'].evaluate(placeholder_args)
        show_tokens = {k: v.evaluate(placeholder_args) for k, v in show_settings['show_tokens'].items()}

        show_config = self.machine.show_controller.create_show_config(
            show, show_settings['priority'], show_settings['speed'], show_settings['loops'], show_settings['sync_ms'],
            show_settings['manual_advance'], show_tokens, show_settings['events_when_played'],
            show_settings['events_when_stopped'], show_settings['events_when_looped'],
            show_settings['events_when_paused'], show_settings['events_when_resumed'],
            show_settings['events_when_advanced'], show_settings['events_when_stepped_back'],
            show_settings['events_when_updated'], show_settings['events_when_completed'])

        previous_show = instance_dict.get(key, None)

        instance_dict[key] = self.machine.show_controller.replace_or_advance_show(previous_show, show_config,
                                                                                  start_step, start_time,
                                                                                  start_running, stop_callback)

    # pylint: disable-msg=too-many-arguments
    def _queue(self, key, instance_dict, show, show_settings, queue, start_time, placeholder_args):
        del queue
        del instance_dict
        del start_time
        del key
        if show_settings['block_queue']:
            raise AssertionError("Cannot use queue with block_queue.")

        start_step = show_settings['start_step'].evaluate(placeholder_args)
        show_tokens = {k: v.evaluate(placeholder_args) for k, v in show_settings['show_tokens'].items()}

        show_config = self.machine.show_controller.create_show_config(
            show, show_settings['priority'], show_settings['speed'], show_settings['loops'], show_settings['sync_ms'],
            show_settings['manual_advance'], show_tokens, show_settings['events_when_played'],
            show_settings['events_when_stopped'], show_settings['events_when_looped'],
            show_settings['events_when_paused'], show_settings['events_when_resumed'],
            show_settings['events_when_advanced'], show_settings['events_when_stepped_back'],
            show_settings['events_when_updated'], show_settings['events_when_completed'])

        show_settings["show_queue"].enqueue_show(show_config, start_step)

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
                speed=show_settings.get('speed'),
                manual_advance=show_settings.get('manual_advance')
            )

    # pylint: disable-msg=too-many-arguments
    def _update_show(self, show, show_settings, context, queue, start_time, placeholder_args):
        instance_dict = self._get_instance_dict(context)
        if 'key' in show_settings and show_settings['key']:
            key = show_settings['key']
        else:
            key = show

        try:
            action = self._actions[show_settings['action']]
        except KeyError:
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
