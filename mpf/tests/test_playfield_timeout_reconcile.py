import asyncio

from mpf.tests.MpfTestCase import MpfTestCase


class TestPlayfieldTimeoutReconcile(MpfTestCase):

    def get_config_file(self):
        return 'null.yaml'

    def test_reconcile_available_balls(self):
        # Ensure the machine is initialized
        self.assertIsNotNone(self.machine)

        playfield = list(self.machine.playfields.values())[0]

        # Simulate stale state: authoritative `balls` is 0 but `available_balls`
        # is 1 (left over from an eject timeout)
        playfield.balls = 0
        playfield.available_balls = 1

        # Start the waiter and let the test loop run briefly
        fut = asyncio.ensure_future(self.machine.ball_controller.wait_until_playfields_are_empty())
        self.machine_run()

        # After a single run the reconciler should have fixed available_balls
        self.assertTrue(fut.done())
        fut.result()
        self.assertEqual(playfield.available_balls, 0)
