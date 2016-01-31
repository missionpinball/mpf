from mock import MagicMock
from mpf.devices.switch import Switch
from mpf.system.device_manager import DeviceCollection

from tests.MpfTestCase import MpfTestCase

class TestMpfTestCase(MpfTestCase):

    def getConfigFile(self):
        return 'test_mpftestcase.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/mpftestcase/'

    def get_platform(self):
        return 'smart_virtual'

    def test_test_case(self):
        # test the delay
        self.delay_callback = MagicMock()
        self.machine.default_platform.delay.add(ms=500,
                                                callback=self.delay_callback)

        self.advance_time_and_run(.25)
        self.delay_callback.assert_not_called()

        self.advance_time_and_run(1)
        self.delay_callback.assert_called_once_with()

        # test the timed switch event
        self.assertIn('switch1', self.machine.switches)
        self.switch_callback = MagicMock()
        self.machine.switch_controller.add_switch_handler('switch1',
                                               self.switch_callback, ms=1000)

        self.machine.switch_controller.process_switch('switch1')
        self.advance_time_and_run(.5)
        self.switch_callback.assert_not_called()

        self.advance_time_and_run(1)
        self.switch_callback.assert_called_once_with()

    def test_multiples(self):
        # test multiples and jump ahead to see if they were called
        self.id_list = list()

        self.machine.default_platform.delay.add(ms=500,
                                                callback=self.test_callback,
                                                id='d1')
        self.machine.default_platform.delay.add(ms=1500,
                                                callback=self.test_callback,
                                                id='d2')
        self.machine.default_platform.delay.add(ms=2500,
                                                callback=self.test_callback,
                                                id='d3')

        self.machine.switch_controller.add_switch_handler('switch1',
            self.test_callback, ms=1000, callback_kwargs={'id': 's1'})
        self.machine.switch_controller.add_switch_handler('switch1',
            self.test_callback, ms=2000, callback_kwargs={'id': 's2'})
        self.machine.switch_controller.add_switch_handler('switch1',
            self.test_callback, ms=3000, callback_kwargs={'id': 's3'})

        self.machine.switch_controller.process_switch('switch1')
        self.advance_time_and_run(10)

        print(self.id_list)

        # make sure the callback was called in the right order
        self.assertEqual(self.id_list[0][0], 'd1')
        self.assertEqual(self.id_list[1][0], 's1')
        self.assertEqual(self.id_list[2][0], 'd2')
        self.assertEqual(self.id_list[3][0], 's2')
        self.assertEqual(self.id_list[4][0], 'd3')
        self.assertEqual(self.id_list[5][0], 's3')

        # make sure they were all called about 500ms apart
        self.assertAlmostEqual(self.id_list[1][1] - self.id_list[0][1], .5,
                               delta=0.01)
        self.assertAlmostEqual(self.id_list[2][1] - self.id_list[1][1], .5,
                               delta=0.01)
        self.assertAlmostEqual(self.id_list[3][1] - self.id_list[2][1], .5,
                               delta=0.01)
        self.assertAlmostEqual(self.id_list[4][1] - self.id_list[3][1], .5,
                               delta=0.01)
        self.assertAlmostEqual(self.id_list[5][1] - self.id_list[4][1], .5,
                               delta=0.01)

    def test_callback(self, id):
        # print(self.id_list)
        self.id_list.append((id, self.machine.clock.time()))
