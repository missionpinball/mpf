#ball_save.py


class BallSave(object):

    def __init__(self, game):
        self.game = game
        self.active = False

        # register for events
        # ball_drain
        # timers_pause
        # timers_resume
        # valid_playfield

    def enable(self, time=None, balls=None):
        pass

    def ball_drain(self, balls):


        self.log.debug("ball save active: %s", self.flag_ball_save_active)
        self.log.debug("num balls to save: %s", self.num_balls_to_save)

        if self.num_balls_in_play:  # if there was at least one BIP
            if self.flag_ball_save_active:  # if ball save is active
                # nope, should post event saying we got one, then let
                # other modes potentially kick in? Do a boolean event?
                self.log.debug("Ball save is active")
                if self.num_balls_to_save == -1:  # save all the new balls
                    self.log.debug("We drained %s new balls and"
                                     " will save all of them",
                                     new_balls)
                    while new_balls > 0:
                        self.save_ball()
                        new_balls -= 1
                else:  # save the balls but count down as we do
                    self.log.debug("We drained %s new balls and will save %s "
                                   "of them", new_balls,
                                   self.num_balls_to_save)
                    while self.num_balls_to_save > 0 and new_balls > 0:
                        self.save_ball()
                        new_balls -= 1
                        self.num_balls_to_save -= 1



        return {'balls': balls}