"""MPF plugin that puts a pyglet window on the screen."""

# lcd.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework
import logging
import version
import locale

global import_success

try:
    import pyglet
    import_success = True
except:
    import_success = False


def preload_check(machine):

    if import_success:
        return True
    else:
        return False


class LCD(object):

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('LCD')
        self.window_items = []
        self.current_ball = None
        self.current_player = None
        self.current_score = None

        locale.setlocale(locale.LC_ALL, '')

        if 'height' not in self.machine.config['LCD']:
            self.machine.config['LCD']['height'] = 800
        if 'width' not in self.machine.config['LCD']:
            self.machine.config['LCD']['width'] = 600
        if 'title' not in self.machine.config['LCD']:
            self.machine.config['LCD']['title'] = 'Mission Pinball Framework'
        if 'items' in self.machine.config['LCD']:
            self.machine.config['LCD']['items'] = (
                self.machine.config['LCD']['items'].split(' '))

        self.setup_window()

        # Register for events
        self.machine.events.add_handler('timer_tick', self.tick)

        if 'player' in self.machine.config['LCD']['items']:
            self.machine.events.add_handler('player_turn_start',
                                            self.update_player)

        if 'score' in self.machine.config['LCD']['items']:
            self.machine.events.add_handler('score_change',
                                            self.update_score)

        if 'ball' in self.machine.config['LCD']['items']:
            self.machine.events.add_handler('ball_starting',
                                            self.update_ball)

    def setup_window(self):

        if not hasattr(self.machine, 'window'):
            self.machine.window = pyglet.window.Window(resizable=True)

        self.machine.window.width = self.machine.config['LCD']['width']
        self.machine.window.height = self.machine.config['LCD']['height']
        self.machine.window.set_caption(self.machine.config['LCD']['title'])

        @self.machine.window.event
        def on_close():
            self.machine.done = True

        @self.machine.window.event
        def on_draw():
            self.machine.window.clear()

            if 'title' in self.machine.config['LCD']:
                self.title = pyglet.text.Label(self.machine.config['LCD']['title'],
                                            font_name='Ariel',
                                            font_size=36,
                                            x=self.machine.window.width//2,
                                            y=self.machine.window.height - 20,
                                            anchor_x='center',
                                            anchor_y='center')
                self.title.draw()

            if 'version' in self.machine.config['LCD']['items']:
                self.version = pyglet.text.Label('Mission Pinball Framework v'
                                                 + version.__version__,
                                            font_name='Ariel',
                                            font_size=12,
                                            x=self.machine.window.width-2,
                                            y=2,
                                            anchor_x='right',
                                            anchor_y='bottom')
                self.version.draw()

            if 'looprate' in self.machine.config['LCD']['items']:
                self.looprate = pyglet.text.Label('Loop Rate: ' +
                                            str(self.machine.loop_rate) +
                                            'Hz',
                                            font_name='Ariel',
                                            font_size=12,
                                            x=2,
                                            y=2,
                                            anchor_x='left',
                                            anchor_y='bottom')
                self.looprate.draw()

            if 'mpf_load' in self.machine.config['LCD']['items']:
                self.mpf_load = pyglet.text.Label('MPF Load: ' +
                                            str(self.machine.mpf_load) +
                                            '%',
                                            font_name='Ariel',
                                            font_size=12,
                                            x=200,
                                            y=2,
                                            anchor_x='left',
                                            anchor_y='bottom')
                self.mpf_load.draw()

            if ('player' in self.machine.config['LCD']['items'] and
                    self.current_player):
                self.player = pyglet.text.Label('Player: ' + str(self.current_player),
                                            font_name='Ariel',
                                            font_size=36,
                                            x=self.machine.window.width*.25,
                                            y=self.machine.window.height - 350,
                                            anchor_x='center',
                                            anchor_y='top')
                self.player.draw()

            if ('ball' in self.machine.config['LCD']['items'] and
                    self.current_ball):
                self.ball = pyglet.text.Label('Ball: ' + str(self.current_ball),
                                            font_name='Ariel',
                                            font_size=36,
                                            x=self.machine.window.width*.75,
                                            y=self.machine.window.height - 350,
                                            anchor_x='center',
                                            anchor_y='top')
                self.ball.draw()

            if ('score' in self.machine.config['LCD']['items'] and
                    self.current_score is not None):
                self.score = pyglet.text.Label(locale.format("%d",
                                            self.current_score, grouping=True),
                                            font_name='Ariel',
                                            font_size=70,
                                            x=self.machine.window.width//2,
                                            y=self.machine.window.height - 150,
                                            anchor_x='center',
                                            anchor_y='top')
                self.score.draw()

    def update_player(self):
        self.current_player = self.machine.game.player.vars['number']
        self.update_ball()
        self.update_score()

    def update_ball(self, **kwargs):
        self.current_ball = self.machine.game.player.vars['ball']

    def update_score(self, change=None, score=None):
        self.current_score = self.machine.game.player.vars['score']

    def tick(self):
        pyglet.clock.tick()

        for window in pyglet.app.windows:
            window.switch_to()
            window.dispatch_events()
            window.dispatch_event('on_draw')
            window.flip()
