import asyncio

from mpf.platforms.rpi import rpi
from mpf.tests.MpfTestCase import MpfTestCase


class MockApigpio():

    # gpio Pull Up Down

    PUD_OFF = 0
    PUD_DOWN = 1
    PUD_UP = 2

    # gpio modes

    INPUT = 0
    OUTPUT = 1

    # gpio edges

    RISING_EDGE = 0
    FALLING_EDGE = 1
    EITHER_EDGE = 2

    class Pi():

        def __init__(self, loop=None):
            del loop
            self.callbacks = {}
            self.modes = {}
            self.pull_ups = {}
            self.servos = {}
            self.outputs = {}
            self.i2c_write = []
            self.i2c_read = []

        @asyncio.coroutine
        def connect(self, address):
            pass

        @asyncio.coroutine
        def read_bank_1(self):
            ## all switches read 1 which means they are open because of the pull-up
            return 0xFF

        @asyncio.coroutine
        def set_pull_up_down(self, gpio, pud):
            self.pull_ups[gpio] = pud

        @asyncio.coroutine
        def set_mode(self, gpio, mode):
            self.modes[gpio] = mode

        @asyncio.coroutine
        def add_callback(self, user_gpio, edge=0, func=None):
            self.callbacks[user_gpio] = func

        @asyncio.coroutine
        def set_servo_pulsewidth(self, user_gpio, pulsewidth):
            self.servos[user_gpio] = pulsewidth

        @asyncio.coroutine
        def write(self, gpio, level):
            self.outputs[gpio] = level

        @asyncio.coroutine
        def set_PWM_dutycycle(self, user_gpio, dutycycle):
            self.outputs[user_gpio] = dutycycle / 255

        @asyncio.coroutine
        def stop(self):
            pass

        @asyncio.coroutine
        def i2c_open(self, bus, address):
            return bus, address

        @asyncio.coroutine
        def i2c_close(self, handle):
            return

        @asyncio.coroutine
        def i2c_write_byte_data(self, handle, register, data):
            """Write byte to i2c register on handle."""
            self.i2c_write.append((handle, register, data))

        @asyncio.coroutine
        def i2c_read_byte_data(self, handle, register):
            """Write byte to i2c register on handle."""
            return self.i2c_read.pop(0)


class TestRpi(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/rpi/'

    def get_platform(self):
        return False

    def setUp(self):
        self.expected_duration = 1.5
        rpi.apigpio = MockApigpio
        super().setUp()

        self.pi = self.machine.default_platform.pi  # type: MockApigpio.Pi

    def testPlatform(self):
        # check modes
        self.assertEqual({1: MockApigpio.INPUT,
                          2: MockApigpio.OUTPUT,
                          7: MockApigpio.INPUT,
                          23: MockApigpio.OUTPUT,
                          30: MockApigpio.OUTPUT},
                         self.pi.modes)

        # check pull ups
        self.assertEqual({1: MockApigpio.PUD_UP,
                          2: MockApigpio.PUD_OFF,
                          7: MockApigpio.PUD_UP,
                          23: MockApigpio.PUD_OFF,
                          30: MockApigpio.PUD_OFF},
                         self.pi.pull_ups)

        # test switches
        self.assertSwitchState("s_test", False)
        self.assertSwitchState("s_test2", False)

        self.pi.callbacks[1](gpio=1, level=1, tick=123)
        self.machine_run()

        self.assertSwitchState("s_test", True)
        self.assertSwitchState("s_test2", False)

        self.pi.callbacks[1](gpio=1, level=0, tick=127)
        self.pi.callbacks[1](gpio=7, level=1, tick=127)
        self.machine_run()

        self.assertSwitchState("s_test", False)
        self.assertSwitchState("s_test2", True)

        # pulse coil
        self.machine.coils["c_test"].pulse()
        self.machine_run()
        self.assertEqual(1, self.pi.outputs[23])
        self.advance_time_and_run(.022)
        self.assertEqual(1, self.pi.outputs[23])
        self.advance_time_and_run(.002)
        self.assertEqual(0, self.pi.outputs[23])

        # enable coil
        self.machine.coils["c_test_allow_enable"].enable()
        self.machine_run()
        self.assertEqual(1, self.pi.outputs[30])
        self.advance_time_and_run(2)
        self.assertEqual(1, self.pi.outputs[30])

        # disable again
        self.machine.coils["c_test_allow_enable"].disable()
        self.machine_run()
        self.assertEqual(0, self.pi.outputs[30])

        # enable with pwm (10ms pulse and 20% duty)
        self.machine.coils["c_pwm"].enable()
        self.machine_run()
        self.assertEqual(1, self.pi.outputs[2])
        self.advance_time_and_run(.01)
        self.assertEqual(0.2, self.pi.outputs[2])

        # test servo
        self.machine.servos["servo1"].go_to_position(0.2)
        self.machine_run()
        self.assertEqual(1200, self.pi.servos[10])

        self.machine.servos["servo1"].go_to_position(0)
        self.machine_run()
        self.assertEqual(1000, self.pi.servos[10])

        self.machine.servos["servo1"].go_to_position(1.0)
        self.machine_run()
        self.assertEqual(2000, self.pi.servos[10])

        device = self.loop.run_until_complete(self.machine.default_platform.configure_i2c("0-123"))

        device.i2c_write8(43, 1337)
        self.machine_run()
        self.assertEqual(((0, 123), 43, 1337), self.pi.i2c_write[0])
        self.pi.i2c_read.append(1337)
        result = self.loop.run_until_complete(device.i2c_read8(43))
        self.assertEqual(1337, result)
