"""MPF plugin which uses lights to represent Game functions. Typically in an
EM machine"""
# info_lights.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging


class InfoLights(object):

    def __init__(self, machine):
        self.log = logging.getLogger('infolights')
        self.machine = machine

        try:
            self.config = self.machine.config['infolights']
        except KeyError:
            return

        self.flash = [
            {'color': 'ff', 'time': 1},
            {'color': '0', 'time': 1},
        ]

        # convert any light names we find to objects
        for k, v in self.config.iteritems():
            if 'light' in v:
                if v['light'] in self.machine.lights:
                    self.config[k]['light'] = self.machine.lights[v['light']]

        self.machine.events.add_handler('ball_started', self.ball_started)
        self.machine.events.add_handler('game_ended', self.game_ended)
        self.machine.events.add_handler('machineflow_Game_start',
                                        self.game_starting)
        self.machine.events.add_handler('player_add_success', self.player_added)
        self.machine.events.add_handler('tilt', self.tilt)
        self.machine.events.add_handler('match', self.match)

        self.game_ended()  # set the initial lights to the game ended state

    def reset_game_lights(self):
        self.log.debug("reset_game_lights")
        # turn off the game-specific lights (player, ball & match)
        for k, v in self.config.iteritems():
            if k.startswith('ball_'):
                v['light'].off()
            if k.startswith('player_'):
                v['light'].off()
            if k.startswith('match_'):
                v['light'].off()

    def ball_started(self):
        self.log.debug("ball_started")
        # turn off all the ball lights
        for k, v in self.config.iteritems():
            if k.startswith('ball_'):
                v['light'].off()

        # turn on this current ball's light
        ball_light = 'ball_' + str(self.machine.game.player.ball)
        if ball_light in self.config:
            self.config[ball_light]['light'].on()

        # turn off the tilt light
        if 'tilt' in self.config:
            self.config['tilt']['light'].off()

    def game_ended(self):
        self.log.debug("game_ended")
        self.reset_game_lights()

        # turn on game over
        if 'game_over' in self.config:
            self.machine.show_controller.run_script(
                lightname=self.config['game_over']['light'].name,
                script=self.flash,
                tps=2)

    def game_starting(self, **kwargs):
        self.log.debug("game_starting")
        self.reset_game_lights()

        # turn off game over
        if 'game_over' in self.config:
            self.machine.show_controller.stop_script(
                lightname=self.config['game_over']['light'].name)
            self.config['game_over']['light'].off()
            # todo is the above right? Should add hold=False to script?

    def player_added(self, player):
        self.log.debug("player_added. player=%s", player)
        player_str = 'player_' + str(player.number)
        self.log.debug("player_str: %s", player_str)
        if player_str in self.config:
            self.config[player_str]['light'].on()

    def tilt(self):
        self.log.debug("tilt")
        if 'tilt' in self.config:
            self.config['tilt']['light'].on()

    def match(self, match):
        self.log.debug("Match")
        match_str = 'match_' + str(match)
        if match_str in self.config:
            self.config[match_str]['light'].on()


plugin_class = InfoLights


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
