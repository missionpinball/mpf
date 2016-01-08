from .MpfTestCase import MpfTestCase


class TestShowController(MpfTestCase):

    def getConfigFile(self):
        return 'test_shows.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/show_controller/'

    def __init__(self, test_map):
        super(TestShowController, self).__init__(test_map)

    def testStartShow(self):
        # Make sure attract mode has been loaded
        self.assertIn('attract', self.machine.modes)

        # Make sure test_show1 has been loaded
        self.assertIn('test_show1', self.machine.shows)

        # Start attract mode (should automatically start the test_show1 light show)
        self.machine.events.post('start_attract')
        self.advance_time_and_run()

