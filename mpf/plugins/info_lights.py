"""MPF plugin which uses lights to represent Game functions. Typically in an
EM machine"""

import logging


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

        self.flash = [
            {'color': 'ff', 'tocks': 1},
            {'color': '0', 'tocks': 1},
        ]

        # convert any light names we find to objects
        for k, v in self.config.items():
            if 'light' in v:
                if v['light'] in self.machine.lights:
                    self.config[k]['light'] = self.machine.lights[v['light']]

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
        for k, v in self.config.items():
            if k.startswith('ball_'):
                v['light'].off()
            if k.startswith('player_'):
                v['light'].off()
            if k.startswith('match_'):
                v['light'].off()

    def ball_started(self, **kwargs):
        self.log.debug("ball_started")
        # turn off all the ball lights
        for k, v in self.config.items():
            if k.startswith('ball_'):
                v['light'].off()

        # turn on this current ball's light
        ball_light = 'ball_' + str(self.machine.game.player.ball)
        if ball_light in self.config:
            self.config[ball_light]['light'].on()

        # turn off the tilt light
        if 'tilt' in self.config:
            self.config['tilt']['light'].off()

    def game_ended(self, **kwargs):
        self.log.debug("game_ended")
        self.reset_game_lights()

        # turn on game over
        if 'game_over' in self.config:
            self.machine.light_controller.run_script(
                lights=self.config['game_over']['light'].name,
                script=self.flash,
                tocks_per_sec=2,
                key='game_over')

    def game_starting(self, **kwargs):
        self.log.debug("game_starting")
        self.reset_game_lights()
        self.machine.light_controller.stop_script(key='game_over')

    def player_added(self, player, **kwargs):
        self.log.debug("player_added. player=%s", player)
        player_str = 'player_' + str(player.number)
        self.log.debug("player_str: %s", player_str)
        if player_str in self.config:
            self.config[player_str]['light'].on()

    def tilt(self, **kwargs):
        self.log.debug("tilt")
        if 'tilt' in self.config:
            self.config['tilt']['light'].on()

    def match(self, match, **kwargs):
        self.log.debug("Match")
        match_str = 'match_' + str(match)
        if match_str in self.config:
            self.config[match_str]['light'].on()


plugin_class = InfoLights
