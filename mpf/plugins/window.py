"""Mission Pinball Framework plugin that puts a pyglet Window on the screen."""

# machine_mode.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework
import logging
import pyglet
import version


class Window(object):

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('Window')
        self.window_items = []
        self.current_ball = ''
        self.current_player = ''
        self.current_score = ''

        if 'height' not in self.machine.config['Window']:
            self.machine.config['Window']['height'] = 800
        if 'width' not in self.machine.config['Window']:
            self.machine.config['Window']['width'] = 600
        if 'title' not in self.machine.config['Window']:
            self.machine.config['Window']['title'] = 'Mission Pinball Framework'
        if 'items' in self.machine.config['Window']:
            self.machine.config['Window']['items'] = (
                self.machine.config['Window']['items'].split(' '))

        self.setup_window()

        # Register for events
        self.machine.events.add_handler('timer_tick', self.tick)

        if 'player' in self.machine.config['Window']['items']:
            self.machine.events.add_handler('player_turn_start',
                                            self.update_player)

        if 'score' in self.machine.config['Window']['items']:
            self.machine.events.add_handler('score_change',
                                            self.update_score)

        if 'ball' in self.machine.config['Window']['items']:
            self.machine.events.add_handler('ball_startin',
                                            self.update_ball)

    def setup_window(self):

        if not hasattr(self.machine, 'window'):
            self.machine.window = pyglet.window.Window(resizable=True)

        self.machine.window.width = self.machine.config['Window']['width']
        self.machine.window.height = self.machine.config['Window']['height']
        self.machine.window.set_caption(self.machine.config['Window']['title'])

        @self.machine.window.event
        def on_close():
            self.machine.done = True

        @self.machine.window.event
        def on_draw():
            self.machine.window.clear()

            if 'title' in self.machine.config['Window']:
                self.label = pyglet.text.Label(self.machine.config['Window']['title'],
                                            font_name='Ariel',
                                            font_size=36,
                                            x=self.machine.window.width//2,
                                            y=self.machine.window.height - 20,
                                            anchor_x='center',
                                            anchor_y='center')
                self.label.draw()
            if 'version' in self.machine.config['Window']['items']:
                self.version = pyglet.text.Label('Mission Pinball Framework v'
                                                 + version.__version__,
                                            font_name='Ariel',
                                            font_size=12,
                                            x=self.machine.window.width-2,
                                            y=2,
                                            anchor_x='right',
                                            anchor_y='bottom')
                self.version.draw()

            if 'player' in self.machine.config['Window']['items']:
                self.player = pyglet.text.Label('Player: ' + str(self.current_player),
                                            font_name='Ariel',
                                            font_size=36,
                                            x=0,
                                            y=self.machine.window.height - 100,
                                            anchor_x='left',
                                            anchor_y='top')
                self.player.draw()

            if 'ball' in self.machine.config['Window']['items']:
                self.ball = pyglet.text.Label('Ball: ' + str(self.current_ball),
                                            font_name='Ariel',
                                            font_size=36,
                                            x=0,
                                            y=self.machine.window.height - 160,
                                            anchor_x='left',
                                            anchor_y='top')
                self.ball.draw()

            if 'score' in self.machine.config['Window']['items']:
                self.score = pyglet.text.Label('Score: ' + str(self.current_score),
                                            font_name='Ariel',
                                            font_size=36,
                                            x=0,
                                            y=self.machine.window.height - 220,
                                            anchor_x='left',
                                            anchor_y='top')
                self.score.draw()

    def update_player(self):
        self.current_player = self.machine.game.player.vars['number']
        self.update_ball()
        self.update_score()

    def update_ball(self):
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
