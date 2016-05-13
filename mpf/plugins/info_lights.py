"""MPF plugin which uses lights to represent Game functions. Typically in an
EM machine"""

import logging

from mpf.devices.led import Led


class InfoLights(object):

    def __init__(self, machine):
        self.log = logging.getLogger('infolights')
        self.machine = machine

        try:
            self.config = self.machine.config['info_lights']
        except KeyError:
            self.machine.log.debug('"info_lights:" section not found in machine '
                                   'configuration, so the Info Lights plugin '
                                   'will not be used.')
            return

        self.machine.events.add_handler('machine_reset_phase_3', self._initialize)

    def _initialize(self):
        # convert any light names we find to objects
        for key, value in self.config.items():
            if 'light' in value:
                if value['light'] in self.machine.lights:
                    self.config[key]['light'] = self.machine.lights[value['light']]
                elif value['light'] in self.machine.leds:
                    self.config[key]['light'] = self.machine.leds[value['light']]
                else:
                    raise AssertionError("Invalid light or led {}".format(value['light']))

        self.machine.events.add_handler('ball_started', self.ball_started)
        self.machine.events.add_handler('game_ended', self.game_ended)
        self.machine.events.add_handler('game_starting', self.game_starting)
        self.machine.events.add_handler('player_add_success', self.player_added)
        self.machine.events.add_handler('tilt', self.tilt)
        self.machine.events.add_handler('match', self.match)

        self.game_ended()  # set the initial lights to the game ended state

    def reset_game_lights(self):
        self.log.debug("reset_game_lights")
        # turn off the game-specific lights (player, ball & match)
        for key, value in self.config.items():
            if key.startswith('ball_'):
                value['light'].off()
            if key.startswith('player_'):
                value['light'].off()
            if key.startswith('match_'):
                value['light'].off()

    def ball_started(self, **kwargs):
        del kwargs
        self.log.debug("ball_started")
        # turn off all the ball lights
        for key, value in self.config.items():
            if key.startswith('ball_'):
                value['light'].off()

        # turn on this current ball's light
        ball_light = 'ball_' + str(self.machine.game.player.ball)
        if ball_light in self.config:
            self.config[ball_light]['light'].on()

        # turn off the tilt light
        if 'tilt' in self.config:
            self.config['tilt']['light'].off()

    def game_ended(self, **kwargs):
        del kwargs
        self.log.debug("game_ended")
        self.reset_game_lights()

        # turn on game over
        if 'game_over' in self.config:
            if isinstance(self.config['game_over']['light'], Led):
                self.machine.shows['flash'].play(
                    show_tokens=dict(leds=self.config['game_over']['light']),
                    key='infolights_game_over')
            else:
                self.machine.shows['flash'].play(
                    show_tokens=dict(lights=self.config['game_over']['light']),
                    key='infolights_game_over')

    def game_starting(self, **kwargs):
        del kwargs
        self.log.debug("game_starting")
        self.reset_game_lights()
        if self.machine.show_controller.get_running_shows('infolights_game_over'):
            self.machine.show_controller.get_running_shows('infolights_game_over')[0].stop()

    def player_added(self, player, **kwargs):
        del kwargs
        self.log.debug("player_added. player=%s", player)
        player_str = 'player_' + str(player.number)
        self.log.debug("player_str: %s", player_str)
        if player_str in self.config:
            self.config[player_str]['light'].on()

    def tilt(self, **kwargs):
        del kwargs
        self.log.debug("tilt")
        if 'tilt' in self.config:
            self.config['tilt']['light'].on()

    def match(self, match, **kwargs):
        del kwargs
        self.log.debug("Match")
        match_str = 'match_' + str(match)
        if match_str in self.config:
            self.config[match_str]['light'].on()


plugin_class = InfoLights
