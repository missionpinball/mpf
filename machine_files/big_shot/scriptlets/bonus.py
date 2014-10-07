# Bonus mode Scriptlet for Big Shot

from mpf.system.scriptlet import Scriptlet
from mpf.system.tasks import DelayManager


class Bonus(Scriptlet):

    def on_load(self):
        self.queue = None
        self.delay = DelayManager()
        self.bonus_lights = list()
        self.bonus_value = 0

        # register a hook into ball_ending
        self.machine.events.add_handler('ball_ending', self.prepare_bonus, 2)

    def prepare_bonus(self, queue):
        self.log.debug("Entering the Big Shot Bonus Sequence")

        if self.machine.tilted:
            self.log.debug("Ball has tilted. No bonus for you!")
            return

        self.set_bonus_value()

        # calculate the bonus value for this ball
        for target in self.machine.drop_target_banks['Solids'].targets:
            if target.complete:
                self.log.debug("Drop Target '%s' is down", target.name)
                self.bonus_lights.append(target.config['light'])

        if self.machine.lights['ball8'].state['brightness']:
            self.log.debug("Eight Ball Target was hit")
            self.bonus_lights.append(self.machine.lights['ball8'])

        for target in self.machine.drop_target_banks['Stripes'].targets:
            if target.complete:
                self.log.debug("Drop Target '%s' is down", target.name)
                self.bonus_lights.append(target.config['light'])

        # if we have bonus to do, register a ball_ending wait
        if self.bonus_lights:
            self.log.debug("Registering a wait since we have bonus light(s)")
            self.queue = queue
            self.queue.wait()

            reels = self.machine.score_reel_controller.active_scorereelgroup

            # Check to see if any of the score reels are busy
            if not reels.valid:
                self.log.debug("Found a score reel group that's not valid. "
                               "We'll wait...")
                self.machine.events.add_handler(
                    'scorereelgroup_' + reels.name + '_valid',
                    self.start_bonus)
            else:
                self.log.debug("Reels are valid. Starting now")
                # If they're not busy, start the bonus now
                self.start_bonus()

    def start_bonus(self, **kwargs):
        # remove the handler that we used to wait for the score reels to be done
        self.machine.events.remove_handler(self.start_bonus)

        reels = self.machine.score_reel_controller.active_scorereelgroup

        # add the handler that will advance through these bonus steps
        self.machine.events.add_handler('scorereelgroup_' + reels.name +
                                        '_valid', self.bonus_step)

        # do the first bonus step to kick off this process
        self.bonus_step()

    def bonus_step(self, **kwargs):
        # automatically called when the score reels are valid

        if self.bonus_lights:
            # sets the "pause" between bonus scores, then does the bonus step
            self.delay.add('bonus', 200, self.do_bonus_step)

        else:
            self.bonus_done()

    def do_bonus_step(self):
        this_light = self.bonus_lights.pop()
        self.machine.score.add(self.bonus_value, force=True)
        this_light.off()

    def set_bonus_value(self):
        # Figures out what the bonus score value is based on what ball this is
        # and how many balls the game is set to.

        balls_remaining = (self.machine.config['Game']['Balls per game'] -
                           self.machine.game.player.vars['ball'])

        if balls_remaining > 1:
            self.bonus_value = (self.machine.config['Scoring']
                                ['bonusValue']['Score'])
        elif balls_remaining == 1:
            self.bonus_value = (self.machine.config['Scoring']
                                ['secondToLastBonusValue']['Score'])
        else:
            self.bonus_value = (self.machine.config['Scoring']
                                ['lastBonusValue']['Score'])

    def bonus_done(self):
        self.log.debug("Bonus is done. Clearing queue")
        # Remove any event handlers we were waiting for
        self.machine.events.remove_handler(self.bonus_step)

        self.queue.clear()

    def stop(self):
        pass
