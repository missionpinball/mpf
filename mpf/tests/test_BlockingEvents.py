from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestBlockingEvents(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/blocking_events/'

    def testBlockingInMode(self):
        self.handler = MagicMock()
        self.handler2 = MagicMock()
        self.handler3 = MagicMock()
        self.machine.events.add_handler("event1", self.handler, priority=10, blocking_facility="random")
        self.machine.events.add_handler("event1", self.handler2, priority=150, blocking_facility="random")
        self.machine.events.add_handler("event1", self.handler3, priority=9)

        self.post_event("event1")
        self.advance_time_and_run(.1)
        self.handler.assert_called_with()
        self.handler2.assert_called_with()
        self.handler3.assert_called_with()
        self.handler.reset_mock()
        self.handler2.reset_mock()
        self.handler3.reset_mock()

        self.start_mode("mode1")
        self.advance_time_and_run(.1)
        self.post_event("event1")
        self.advance_time_and_run(.1)
        self.handler.assert_not_called()
        self.handler2.assert_called_with()
        self.handler3.assert_called_with(_min_priority={'all': 100})
        self.handler.reset_mock()
        self.handler2.reset_mock()
        self.handler3.reset_mock()

        self.start_mode("mode2")
        self.advance_time_and_run(.1)
        self.post_event("event1")
        self.advance_time_and_run(.1)
        self.handler.assert_not_called()
        self.handler2.assert_not_called()
        self.handler3.assert_called_with(_min_priority={'all': 200})
        self.handler.reset_mock()
        self.handler2.reset_mock()
        self.handler3.reset_mock()

        self.stop_mode("mode2")
        self.advance_time_and_run(.1)
        self.post_event("event1")
        self.advance_time_and_run(.1)
        self.handler.assert_not_called()
        self.handler2.assert_called_with()
        self.handler3.assert_called_with(_min_priority={'all': 100})

