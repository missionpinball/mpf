import asyncio

from mpf.tests.MpfTestCase import MpfTestCase


class TestEjectTimeoutRepro(MpfTestCase):

    def get_config_file(self):
        return 'null.yaml'

    def test_eject_timeout_decrements_available(self):
        # Setup: pick a source device that will schedule an eject to a target
        trough = self.machine.ball_devices['trough']
        # Ensure starting clean
        trough.available_balls = 6
        trough.balls = 6

        # Choose a playfield target to receive an eject
        playfield = list(self.machine.playfields.values())[0]
        playfield.balls = 0
        playfield.available_balls = 0

        # Simulate a mechanical eject during idle from trough to playfield
        # This uses the code path that increments target.available_balls
        # and enqueues an eject via the outgoing handler.
        # Find a device that supports mechanical eject: call handle_mechanical_eject_during_idle
        # We'll call it on trough to schedule an eject to its default eject target.
        trough.config['eject_targets'][0].available_balls = 0

        # Call handler that increments available_balls and adds eject to queue
        self.machine_run()
        # Call the method directly to simulate mechanical eject scheduling
        self.assertTrue(hasattr(trough, 'handle_mechanical_eject_during_idle'))
        fut = asyncio.ensure_future(trough.handle_mechanical_eject_during_idle())
        # Let the loop run so the outgoing handler processes the queue
        self.advance_time_and_run(0)

        # After scheduling, the target should have been incremented
        target = trough.config['eject_targets'][0]
        self.assertGreaterEqual(target.available_balls, 1)

        # Now simulate the eject timing out: advance time beyond eject timeout
        # and let the outgoing handler run its timeout path.
        # Use a large time to ensure timeout triggers
        self.advance_time_and_run(5)

        # After the timeout and our defensive fix, available_balls should not be left > balls
        # The playfield authoritative balls is 0, so available_balls should be 0 as well
        self.assertEqual(playfield.available_balls, playfield.balls)
