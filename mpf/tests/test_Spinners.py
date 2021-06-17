from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestSpinners(MpfTestCase):

    def get_config_file(self):
        return 'test_spinners.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/spinners/'

    def get_platform(self):
        return 'smart_virtual'

    def test_spinner_active_inactive(self):
        self.mock_event("spinner_spin1_active")
        self.mock_event("spinner_spin1_hit")
        self.mock_event("spinner_spin1_inactive")
        self.mock_event("spinner_spin1_idle")

        self.hit_and_release_switch("switch1")
        self.assertEventCalled("spinner_spin1_active")
        self.assertEventCalled("spinner_spin1_hit")

        self.advance_time_and_run(0.5)
        self.assertEventNotCalled("spinner_spin1_inactive")
        self.assertEventNotCalled("spinner_spin1_idle")

        self.advance_time_and_run(0.5)
        self.assertEventCalled("spinner_spin1_inactive")
        self.assertEventNotCalled("spinner_spin1_idle")

    def test_spinner_active_inactive_idle(self):
        self.mock_event("spinner_spin2_active")
        self.mock_event("spinner_spin2_hit")
        self.mock_event("spinner_spin2_inactive")
        self.mock_event("spinner_spin2_idle")

        self.hit_and_release_switch("switch2")
        self.assertEventCalled("spinner_spin2_active")
        self.assertEventCalled("spinner_spin2_hit")

        self.advance_time_and_run(0.1)
        self.assertEventNotCalled("spinner_spin2_inactive")
        self.assertEventNotCalled("spinner_spin2_idle")

        self.advance_time_and_run(0.4)
        self.assertEventCalled("spinner_spin2_inactive")
        self.assertEventNotCalled("spinner_spin2_idle")

        self.advance_time_and_run(0.5)
        self.assertEventNotCalled("spinner_spin2_idle")

        self.advance_time_and_run(0.4)
        self.assertEventCalled("spinner_spin2_idle")

    def test_single_spinner_hits(self):
        self.mock_event("spinner_spin1_active")
        self.mock_event("spinner_spin1_hit")
        self.mock_event("spinner_spin1_inactive")
        self.mock_event("spinner_spin1_idle")

        self.hit_and_release_switch("switch1")
        self.assertEventCalled("spinner_spin1_active")
        self.assertEventCalled("spinner_spin1_hit")
        self.assertEqual({"hits": 1, "label": None}, self._last_event_kwargs['spinner_spin1_hit'])

        self.hit_and_release_switch("switch1")
        self.advance_time_and_run(0.5)
        self.assertEqual({"hits": 2, "label": None}, self._last_event_kwargs['spinner_spin1_hit'])
        self.assertEventNotCalled("spinner_spin1_inactive")

        self.hit_and_release_switch("switch1")
        self.advance_time_and_run(0.5)
        self.assertEqual({"hits": 3, "label": None}, self._last_event_kwargs['spinner_spin1_hit'])
        self.assertEventNotCalled("spinner_spin1_inactive")

        self.hit_and_release_switch("switch1")
        self.advance_time_and_run(0.5)
        self.assertEqual({"hits": 4, "label": None}, self._last_event_kwargs['spinner_spin1_hit'])
        self.assertEventNotCalled("spinner_spin1_inactive")

        self.advance_time_and_run(0.5)
        self.assertEqual(1, self._events["spinner_spin1_active"])
        self.assertEqual(4, self._events["spinner_spin1_hit"])
        self.assertEventCalled("spinner_spin1_inactive")
        self.assertEventNotCalled("spinner_spin1_idle")

    def test_double_spinner_hits(self):
        self.mock_event("spinner_spin2_active")
        self.mock_event("spinner_spin2_hit")
        self.mock_event("spinner_spin2_foo_hit")
        self.mock_event("spinner_spin2_bar_hit")
        self.mock_event("spinner_spin2_inactive")
        self.mock_event("spinner_spin2_idle")

        self.hit_and_release_switch("switch2")
        self.assertEventCalled("spinner_spin2_active")
        self.assertEventCalled("spinner_spin2_hit")
        self.assertEventCalled("spinner_spin2_foo_hit")
        self.assertEqual({"hits": 1, "label": "foo"}, self._last_event_kwargs['spinner_spin2_hit'])
        self.assertEqual(1, self._events["spinner_spin2_foo_hit"])
        self.assertEqual(0, self._events["spinner_spin2_bar_hit"])

        self.hit_and_release_switch("switch3")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 2, "label": "bar"}, self._last_event_kwargs['spinner_spin2_hit'])
        self.assertEqual(1, self._events["spinner_spin2_foo_hit"])
        self.assertEqual(1, self._events["spinner_spin2_bar_hit"])

        self.hit_and_release_switch("switch3")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 3, "label": "bar"}, self._last_event_kwargs['spinner_spin2_hit'])
        self.assertEqual(1, self._events["spinner_spin2_foo_hit"])
        self.assertEqual(2, self._events["spinner_spin2_bar_hit"])

        self.hit_and_release_switch("switch2")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 4, "label": "foo"}, self._last_event_kwargs['spinner_spin2_hit'])
        self.assertEqual(2, self._events["spinner_spin2_foo_hit"])
        self.assertEqual(2, self._events["spinner_spin2_bar_hit"])
        self.assertEventNotCalled("spinner_spin2_inactive")

        self.advance_time_and_run(0.3)
        self.assertEventCalled("spinner_spin2_inactive")
        self.assertEventNotCalled("spinner_spin2_idle")

        # Re-activate the spinner before it goes idle
        self.hit_and_release_switch("switch2")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 1, "label": "foo"}, self._last_event_kwargs['spinner_spin2_hit'])
        self.assertEqual(3, self._events["spinner_spin2_foo_hit"])
        self.assertEqual(2, self._events["spinner_spin2_bar_hit"])
        # Active should be called again
        self.assertEqual(2, self._events["spinner_spin2_active"])
        self.assertEqual(1, self._events["spinner_spin2_inactive"])
        self.assertEventNotCalled("spinner_spin2_idle")

        self.advance_time_and_run(0.3)
        self.assertEqual(2, self._events["spinner_spin2_active"])
        self.assertEqual(2, self._events["spinner_spin2_inactive"])
        self.assertEventNotCalled("spinner_spin2_idle")

        self.advance_time_and_run(0.5)
        self.assertEventNotCalled("spinner_spin2_idle")

        self.advance_time_and_run(0.3)
        self.assertEventCalled("spinner_spin2_idle")

    def test_reset_when_inactive_false(self):
        self.mock_event("spinner_spin3_active")
        self.mock_event("spinner_spin3_hit")
        self.mock_event("spinner_spin3_inactive")
        self.mock_event("spinner_spin3_idle")

        self.hit_and_release_switch("switch4")
        self.assertEventCalled("spinner_spin3_active")
        self.assertEventCalled("spinner_spin3_hit")
        self.assertEqual({"hits": 1, "label": None}, self._last_event_kwargs['spinner_spin3_hit'])
        self.assertEventNotCalled("spinner_spin3_inactive")

        self.hit_and_release_switch("switch4")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 2, "label": None}, self._last_event_kwargs['spinner_spin3_hit'])
        self.assertEventNotCalled("spinner_spin3_inactive")

        self.hit_and_release_switch("switch4")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 3, "label": None}, self._last_event_kwargs['spinner_spin3_hit'])
        self.assertEventNotCalled("spinner_spin3_inactive")

        self.advance_time_and_run(0.3)
        self.assertEventCalled("spinner_spin3_inactive")
        self.assertEventNotCalled("spinner_spin3_idle")

        # Re-activate the spinner before it goes idle
        self.hit_and_release_switch("switch4")
        self.advance_time_and_run(0.3)
        self.assertEqual({"hits": 4, "label": None}, self._last_event_kwargs['spinner_spin3_hit'])
        # Active should be called again
        self.assertEqual(2, self._events["spinner_spin3_active"])
        self.assertEqual(1, self._events["spinner_spin3_inactive"])
        self.assertEventNotCalled("spinner_spin3_idle")

        self.advance_time_and_run(0.3)
        self.assertEqual(2, self._events["spinner_spin3_active"])
        self.assertEqual(2, self._events["spinner_spin3_inactive"])
        self.assertEventNotCalled("spinner_spin3_idle")

        self.advance_time_and_run(0.5)
        self.assertEventNotCalled("spinner_spin3_idle")

        self.advance_time_and_run(0.3)
        self.assertEventCalled("spinner_spin3_idle")
