from copy import deepcopy

from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):
    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=0,
             play_kwargs=None, **kwargs):

        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        if 'shows' in settings:
            settings = settings['shows']

        settings = deepcopy(settings)

        for show, s in settings.items():

            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            if s['action'].lower() == 'play':
                self.machine.shows[show].play(mode=mode,
                                              play_kwargs=play_kwargs, **s)

            elif s['action'].lower() == 'stop':
                self.machine.shows[show].stop(play_kwargs=play_kwargs, **s)

    def clear(self, caller, priority):
        self.machine.show_controller.stop_shows_by_mode(caller)

    def get_express_config(self, value):
        return dict()

    def check_ok_to_play(self, settings, mode, priority):
        return True

        # todo

        # need a way to figure out whether a show can be played now, or
        # whether it needs to be added to some kind of queue. No idea how to
        # do this.

        # e.g. what if voice track is playing a callout, and you get an
        # extra ball, so the extra ball show wants to play, but it includes
        # display, sound, and light show elements. You don't want to cut off
        # the current voice call, rather you want to queue the show, but you
        # have to queue the whole show, because you don't want the extra ball
        # display and lights to play now while the sound is queued. So really
        # we need a show queue which works like the sound track queue. And
        # those should probably be the same queue

player_cls = ShowPlayer
