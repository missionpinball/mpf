"""Slide config player."""
import asyncio
from mpf.config_players.device_config_player import DeviceConfigPlayer


class SlidePlayer(DeviceConfigPlayer):

    """Config Player for slides."""

    config_file_section = 'slide_player'
    show_section = 'slides'
    allow_placeholders_in_keys = True

    __slots__ = []

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Process a slide_player event."""
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)

        if "slides" in settings:
            raise AssertionError("DEPRECATED setting slides found.")

        for slide, s in settings.items():
            # TODO: is there a case where this has not been expanded?
            if not isinstance(slide, str):
                if slide.condition and not slide.condition.evaluate(kwargs):
                    continue
                slide = slide.name
            else:
                raise AssertionError("WHY?")

            if s["priority"]:
                priority = s["priority"] + priority
            print("XXXXX", slide, s)
            if s["slide"]:
                if "widgets" in s and s["widgets"]:
                    # TODO: improve error
                    raise AssertionError("Cannot use widgets and slides at the same time.")

                slide = s['slide']
                raise AssertionError("TODO: Implement named_slides loading")

            elif s["widgets"]:
                # name of anonymous slides depends on context + event name
                slide = calling_context
                slide_obj = self.machine.media_controller.create_slide(slide, s["widgets"], priority)
                # TODO: add widgets here
            else:
                raise AssertionError("TODO: Implement named_slides loading")

            if s['target']:
                target_name = s['target']
            else:
                target_name = 'default'

            if target_name not in self.machine.targets:
                # Target does not exist yet or is not ready.
                # TODO: improve error
                raise AssertionError("Target {} does not exist".format(target_name))
            elif not self.machine.targets[target_name].ready:
                # Should not happen here
                # TODO: improve error
                raise AssertionError("Target {} is not ready.".format(target_name))

            target = self.machine.targets[target_name]

            if target_name not in instance_dict:
                instance_dict[target_name] = {}

            if s['action'] == 'play':
                # remove slide if it already exists
                if slide in instance_dict[target_name]:
                    future = target.replace_slide(instance_dict[target_name][slide], slide_obj,
                                                  transition_config=s['transition'] if 'transition' in s else [])
                    del instance_dict[target_name][slide]
                else:
                    future = target.add_slide(slide_obj, transition_config=s['transition'] if 'transition' in s else [])
                # run this in the background
                asyncio.ensure_future(future)

                instance_dict[target_name][slide] = slide_obj

            elif s['action'] == 'remove' and slide in instance_dict[target_name]:
                future = target.remove_slide(instance_dict[target_name][slide],
                                             transition_config=s['transition'] if 'transition' in s else [])
                asyncio.ensure_future(future)
                del instance_dict[target_name][slide]

    def _expand_device(self, device):
        # parse conditionals
        devices = super()._expand_device(device)
        for index, device_entry in enumerate(devices):
            if isinstance(device_entry, str):
                devices[index] = self.machine.placeholder_manager.parse_conditional_template(device_entry)
        return devices

    def get_express_config(self, value):
        # express config for slides can either be a string (slide name) or a
        # list (widgets which are put on a new slide)
        if isinstance(value, list):
            return dict(widgets=value)
        else:
            return dict(slide=value)

    def validate_config(self, config):
        """Validates the slide_player: section of a config file (either a
        machine-wide config or a mode config).

        Args:
            config: A dict of the contents of the slide_player section
            from the config file. It's assumed that keys are event names, and
            values are settings for what the slide_player should do when that
            event is posted.

        Returns: A dict a validated entries.

        This method overrides the base method since the slide_player has
        unique options (including lists of widgets or single dict entries that
        are a widget settings instead of slide settings.

        """
        # first, we're looking to see if we have a string, a list, or a dict.
        # if it's a dict, we look to see whether we have a widgets: entry
        # or the name of some slide
        # TODO: clean this up and remove special cases
        validated_config = dict()

        for event, settings in config.items():
            if isinstance(settings, list):
                raise AssertionError(
                    "Config of slide_player for event {} is broken. "
                    "It expects a dict not a list".format(event))

            if not isinstance(settings, dict):
                settings = {settings: dict()}

            for slide, slide_settings in settings.items():
                dict_is_widgets = False

                # if settings is list, it's widgets
                if isinstance(slide_settings, list):
                    # convert it to a dict by moving this list of settings into
                    # a dict key called "widgets"
                    slide_settings = dict(widgets=slide_settings)

                # Now we have a dict, but is this a dict of settings for a
                # single slide, or a dict of settings for the slide player
                # itself?

                # So let's check the keys and see if they're all valid keys
                # for a slide_player. If so, it's slide_player keys. If not,
                # we assume they're widgets for a slide.

                elif isinstance(slide_settings, str):
                    # slide_settings could be a string 'slide: slide_name',
                    # so we rename the key to the slide name with an empty dict
                    if slide_settings == "remove":
                        slide_settings = {"action": "remove"}
                    else:
                        slide = slide_settings
                        slide_settings = dict()

                elif not isinstance(slide_settings, dict):
                    raise AssertionError(
                        "Expected a dict in slide_player {}:{}.".format(event,
                                                                        slide))

                for key in slide_settings:
                    if key not in self.machine.config_validator.get_config_spec()['slide_player']:
                        dict_is_widgets = True
                        break

                if dict_is_widgets:
                    slide_settings = dict(widgets=[slide_settings])

                validated_config[event] = self._validate_config_item(slide, slide_settings)

        return validated_config

    def _validate_config_item(self, device, device_settings):
        validated_dict = super()._validate_config_item(device, device_settings)
        # device is slide name
        for config in validated_dict.values():
            if config['target'] and config['target'] not in self.machine.targets:
                raise AssertionError("Target {} does not exist.".format(config['target']))
            if 'widgets' in config and config["widgets"]:
                if "slide" in config and config["slide"]:
                    raise AssertionError("Cannot use widgets and slide at the same time.")
                pass
                # verify widgets
                # TODO: readd this
                # config['widgets'] = self.machine.widgets.process_config(
                #     config['widgets'])
            else:
                # verify that slide exists
                if config['slide']:
                    slide = config['slide']
                else:
                    slide = self.machine.placeholder_manager.parse_conditional_template(device).name

                raise AssertionError("TODO: implement named slides")
                if config['action'] == "play" and slide not in self.machine.slides:
                    raise AssertionError("Slide {} not found".format(slide))

            # TODO: readd this
            # self.machine.transition_manager.validate_transitions(config)

        return validated_dict

    def clear_context(self, context):
        """Remove all slides from this player context."""
        instance_dict = self._get_instance_dict(context)
        for _, slides in instance_dict.items():
            for slide in slides.values():
                slide.remove()

        self._reset_instance_dict(context)
