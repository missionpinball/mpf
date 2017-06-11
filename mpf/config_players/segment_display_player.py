from mpf.config_players.device_config_player import DeviceConfigPlayer


class SegmentDisplayPlayer(DeviceConfigPlayer):

    """Generates texts """

    config_file_section = 'segment_display_player'
    show_section = 'segment_displays'
    machine_collection_name = 'segment_displays'

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Show text on display"""
        del kwargs
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)

        for display, s in settings.items():
            action = s['action']
            if not display in instance_dict:
                instance_dict[display] = {}

            key = full_context + "." + display.name

            if s['key']:
                key += s['key']

            if action == "add":
                # in case it is already there
                if key in instance_dict[display]:
                    display.remove_text_by_key(key)
                # add text
                display.add_text(s['text'], priority + s['priority'], key)
                instance_dict[display][key] = True
            elif action == "remove":
                if key in instance_dict[display]:
                    display.remove_text_by_key(key)
                    del instance_dict[display][key]
            else:
                raise AssertionError("Invalid action {}".format(action))

    def clear_context(self, context):
        """Remove all texts."""
        full_context = self._get_full_context(context)
        for light in self._get_instance_dict(context).values():
            light.remove_from_stack_by_key(full_context)

        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(action="add", text=value)