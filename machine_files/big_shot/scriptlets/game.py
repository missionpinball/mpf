# Game mode Scriptlet for Big Shot

from mpf.system.scriptlet import Scriptlet


class Game(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Game_start', self.start)
        self.machine.events.add_handler('machineflow_Game_stop', self.stop)

    def start(self):

        self.machine.events.add_handler('collect_special',
                                        self.collect_special)
        self.machine.events.add_handler('player_add_success',
                                        self.player_added)
        self.machine.events.add_handler('ball_started',
                                        self.ball_started)

        # register for classic / modern notification
        self.machine.events.add_handler('enable_classic_mode',
                                        self.enable_classic_mode)
        self.machine.events.add_handler('enable_modern_mode',
                                        self.enable_modern_mode)

        # register shows for cool effects in modern mode
        self.machine.events.add_handler('drop_targets_Solids_lit_hit',
                                        self.solid_target_hit)  # gabe
        self.machine.events.add_handler('drop_targets_Stripes_lit_hit',
                                        self.stripe_target_hit)  # gabe

        # set initial classic / modern mode
        if self.machine.classic_mode:
            self.enable_classic_mode()
        else:
            self.enable_modern_mode()

        # turn on the GI
        for light in self.machine.lights.items_tagged('GI'):
            light.on()

        # Game Over stays on, so we have to turn it off (Gabe did this)
        self.machine.lights['gameOver'].off()

    def enable_classic_mode(self):
        pass

    def enable_modern_mode(self):
        pass

    def stop(self):
        self.machine.events.remove_handler(self.collect_special)
        self.machine.events.remove_handler(self.player_added)
        self.machine.events.remove_handler(self.ball_started)
        self.machine.events.remove_handler(self.enable_classic_mode)
        self.machine.events.remove_handler(self.enable_modern_mode)
        self.machine.events.remove_handler(self.ball_started)
        self.machine.events.remove_handler(self.solid_target_hit)  # gabe
        self.machine.events.remove_handler(self.stripe_target_hit)  # gabe

    def player_added(self, **kwargs):
        self.machine.coils['gameCounter'].pulse()

    def ball_started(self, **kwargs):
        self.log.debug("Game Scriplet ball_started()")

        self.set_bonus_lights()

        # Need this since Big Shot's plunger lane is not a ball device,
        # so we need to automatically launch a "live" ball when the ball
        # starts
        if not self.machine.ball_controller.num_balls_live:
            self.machine.ball_controller.add_live()

        # Gabe put this in because we need to make sure the 8 ball lights
        # are turned off when a ball starts. They seem to have a mind of
        # their own since there's no device attached to them

        self.machine.lights['ball8'].off()
        self.machine.lights['eightBall500'].off()

    def collect_special(self):
        self.machine.coils.knocker.pulse()
        self.machine.game.award_extra_ball()

    def set_bonus_lights(self):
        # Used to set the proper playfield light to show the bonus value for
        # that ball

        balls_remaining = (self.machine.config['Game']['Balls per game'] -
                           self.machine.game.player.vars['ball'])

        if balls_remaining > 1:
            self.machine.lights['bonus1k'].on()
            self.machine.lights['bonus2k'].off()
            self.machine.lights['bonus3k'].off()
        elif balls_remaining == 1:
            self.machine.lights['bonus1k'].off()
            self.machine.lights['bonus2k'].on()
            self.machine.lights['bonus3k'].off()
        else:
            self.machine.lights['bonus1k'].off()
            self.machine.lights['bonus2k'].off()
            self.machine.lights['bonus3k'].on()

    # methods below do cool things when modern mode is on.

    def solid_target_hit(self):  # gabe

        if not self.machine.classic_mode:

            self.machine.shows['solid_target_hit'].play(repeat=False,
                                                       tocks_per_sec=25,
                                                       priority=1001)

    def stripe_target_hit(self):  # gabe

        if not self.machine.classic_mode:

            self.machine.shows['stripe_target_hit'].play(repeat=False,
                                                       tocks_per_sec=25,
                                                       priority=1001)

