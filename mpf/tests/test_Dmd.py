from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
from mpf.tests.MpfTestCase import test_config


class TestDmd(MpfBcpTestCase):

    def getMachinePath(self):
        return 'tests/machine_files/dmd/'

    @test_config("testDmd.yaml")
    def testDmd(self):
        self.machine.dmds.test_dmd.update(b'12345')
        self.assertEqual(b'12345', self.machine.dmds.test_dmd.hw_device.data)

        self._bcp_client.receive_queue.put_nowait(("dmd_frame", {"name": "test_dmd", "rawbytes": b'1337'}))
        self.machine_run()

        self.assertEqual(b'1337', self.machine.dmds.test_dmd.hw_device.data)

    @test_config("testRgbDmd.yaml")
    def testRgbDmd(self):
        self.machine.rgb_dmds.test_dmd.update(b'12345')
        self.assertEqual(b'12345', self.machine.rgb_dmds.test_dmd.hw_device.data)

        self._bcp_client.receive_queue.put_nowait(("rgb_dmd_frame", {"name": "test_dmd", "rawbytes": b'1337'}))
        self.machine_run()

        self.assertEqual(b'1337', self.machine.rgb_dmds.test_dmd.hw_device.data)

        display = self.machine.rgb_dmds.test_dmd
        self.assertEqual(1.0, display.hw_device.brightness)

        self.machine.settings.set_setting_value("dmd_brightness", 0.75)
        self.advance_time_and_run()

        self.assertEqual(0.75, display.hw_device.brightness)
