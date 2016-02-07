# Claw controller Scriptlet for Demo Man

from mpf.core.scriptlet import Scriptlet


class Claw(Scriptlet):

    def on_load(self):

        self.auto_release_in_progress = False

        self.machine.switch_controller.add_switch_handler(
            's_elevator_hold', self.get_ball, ms=100)

        if self.machine.switch_controller.is_active('s_elevator_hold'):
            self.auto_release_in_progress = True
            self.get_ball()

        self.machine.events.add_handler('light_claw', self.light_claw)

    def enable(self):
        print("enable")
        self.machine.switch_controller.add_switch_handler(
            's_flipper_lower_left', self.move_left)
        self.machine.switch_controller.add_switch_handler(
            's_flipper_lower_left', self.stop_moving, state=0)
        self.machine.switch_controller.add_switch_handler(
            's_flipper_lower_right', self.move_right)
        self.machine.switch_controller.add_switch_handler(
            's_flipper_lower_right', self.stop_moving, state=0)
        self.machine.switch_controller.add_switch_handler(
            's_ball_launch', self.release)
        self.machine.switch_controller.add_switch_handler(
            's_claw_position_1', self.stop_moving)

    def disable(self):
        print("disable")
        self.stop_moving()
        self.machine.switch_controller.remove_switch_handler(
            's_flipper_lower_left', self.move_left)
        self.machine.switch_controller.remove_switch_handler(
            's_flipper_lower_left', self.stop_moving, state=0)
        self.machine.switch_controller.remove_switch_handler(
            's_flipper_lower_right', self.move_right)
        self.machine.switch_controller.remove_switch_handler(
            's_flipper_lower_right', self.stop_moving, state=0)
        self.machine.switch_controller.remove_switch_handler(
            's_ball_launch', self.release)
        self.machine.switch_controller.remove_switch_handler(
            's_claw_position_1', self.stop_moving)
        self.machine.switch_controller.remove_switch_handler(
            's_claw_position_1', self.release, state=0)
        self.machine.switch_controller.remove_switch_handler(
            's_claw_position_2', self.release)

    def move_left(self):
        print("move left")
        if (self.machine.switch_controller.is_active('s_claw_position_2') and
                self.machine.switch_controller.is_active('s_claw_position_1')):
            return
        self.machine.coils['c_claw_motor_left'].enable()

    def move_right(self):
        print("move right")
        if (self.machine.switch_controller.is_active('s_claw_position_1') and
                self.machine.switch_controller.is_inactive('s_claw_position_2')):
            return
        self.machine.coils['c_claw_motor_right'].enable()

    def stop_moving(self):
        print("stop moving")
        self.machine.coils['c_claw_motor_left'].disable()
        self.machine.coils['c_claw_motor_right'].disable()

    def release(self):
        print("release")
        self.disable_claw_magnet()
        self.auto_release_in_progress = False
        self.disable()

    def auto_release(self):
        print("auto releasing")
        self.disable()
        if (self.machine.switch_controller.is_active('s_claw_position_2') and
                self.machine.switch_controller.is_active('s_claw_position_1')):
            self.machine.switch_controller.add_switch_handler(
                's_claw_position_1', self.release, state=0)
            # move right, drop when switch 1 opens
            self.move_right()

        elif (self.machine.switch_controller.is_active('s_claw_position_1') and
                self.machine.switch_controller.is_inactive('s_claw_position_2')):
            self.machine.switch_controller.add_switch_handler(
                's_claw_position_2', self.release)
            # move left, drop when switch 2 closes
            self.move_left()

        else:
            self.release()

    def get_ball(self):
        print("get ball")

        if not self.machine.game:
            self.auto_release_in_progress = True

        if not (self.machine.switch_controller.is_active('s_claw_position_1') and
                self.machine.switch_controller.is_inactive('s_claw_position_2')):
            self.move_right()

            self.machine.switch_controller.add_switch_handler(
                's_claw_position_1', self.do_pickup)
        else:
            self.do_pickup()

    def do_pickup(self):
        print("do pickup")
        self.stop_moving()
        self.machine.switch_controller.remove_switch_handler(
            's_claw_position_1', self.do_pickup)
        self.enable_claw_magnet()
        self.machine.coils['c_elevator_motor'].enable()
        self.machine.switch_controller.add_switch_handler('s_elevator_index',
                                                          self.stop_elevator)

        if not self.auto_release_in_progress:
            self.enable()

    def stop_elevator(self):
        print("stop elevator")
        self.machine.coils['c_elevator_motor'].disable()

        if self.auto_release_in_progress:
            self.auto_release()

    def light_claw(self):
        print("light claw")
        #self.machine.ball_devices['elevator'].request_ball()
        self.machine.diverters['diverter'].enable()

    def disable_claw_magnet(self):
        print("disable claw magnet")
        self.machine.coils['c_claw_magnet'].disable()

    def enable_claw_magnet(self):
        print("enabling claw magnet")
        self.machine.coils['c_claw_magnet'].enable()
