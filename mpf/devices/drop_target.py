"""Contains the base classes for drop targets and drop target banks."""

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("complete")
class DropTarget(SystemWideDevice):

    """Represents a single drop target in a pinball machine.

    Args: Same as the `Target` parent class
    """

    config_section = 'drop_targets'
    collection = 'drop_targets'
    class_label = 'drop_target'

    def __init__(self, machine, name):
        """Initialise drop target."""
        self.reset_coil = None
        self.knockdown_coil = None
        self.banks = None
        super().__init__(machine, name)

        self._in_ball_search = False
        self.complete = False
        self.delay = DelayManager(machine.delayRegistry)

    def _initialize(self):
        self.reset_coil = self.config['reset_coil']
        self.knockdown_coil = self.config['knockdown_coil']
        self.banks = set()

        # can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_4',
                                        self._update_state_from_switch)
        self.machine.events.add_handler('init_phase_4',
                                        self._register_switch_handlers)

        # TODO: make playfield name configurable
        self.machine.ball_devices['playfield'].ball_search.register(
            self.config['ball_search_order'], self._ball_search)

    def _ball_search_phase1(self):
        if not self.complete and self.reset_coil:
            self.reset_coil.pulse()
            return True
        # if down. knock down again
        elif self.complete and self.knockdown_coil:
            self.knockdown_coil.pulse()
            return True

    def _ball_search_phase2(self):
        if self.reset_coil and self.knockdown_coil:
            if self.complete:
                self._in_ball_search = True
                self.reset_coil.pulse()
                self.delay.add(100, self._ball_search_knockdown)
                return True
            else:
                self._in_ball_search = True
                self.knockdown_coil.pulse()
                self.delay.add(100, self._ball_search_reset)
                return True
        else:
            # fall back to phase1
            return self._ball_search_phase1()

    def _ball_search_phase3(self):
        if self.complete:
            if self.reset_coil:
                self.reset_coil.pulse()
                if self.knockdown_coil:
                    self._in_ball_search = True
                    self.delay.add(100, self._ball_search_knockdown)
                return True
            else:
                return self._ball_search_phase1()
        else:
            if self.knockdown_coil:
                self.knockdown_coil.pulse()
                if self.reset_coil:
                    self._in_ball_search = True
                    self.delay.add(100, self._ball_search_reset)
                return True
            else:
                return self._ball_search_phase1()

    def _ball_search_iteration_finish(self):
        self._in_ball_search = False

    def _ball_search_knockdown(self):
        self.knockdown_coil.pulse()
        self.delay.add(100, self._ball_search_iteration_finish)

    def _ball_search_reset(self):
        self.reset_coil.pulse()
        self.delay.add(100, self._ball_search_iteration_finish)

    def _ball_search(self, phase, iteration):
        del iteration
        if phase == 1:
            # phase 1: do not change state.
            # if up. reset again
            return self._ball_search_phase1()
        elif phase == 2:
            # phase 2: if we can reset and knockdown the target we will do that
            return self._ball_search_phase2()
        else:
            # phase3: reset no matter what
            return self._ball_search_phase3()

    def _register_switch_handlers(self):
        # register for notification of switch state
        # this is in addition to the parent since drop targets track
        # self.complete in separately

        self.machine.switch_controller.add_switch_handler(
            self.config['switch'].name,
            self._update_state_from_switch, 0)
        self.machine.switch_controller.add_switch_handler(
            self.config['switch'].name,
            self._update_state_from_switch, 1)

    def knockdown(self, **kwargs):
        """Pulse the knockdown coil to knock down this drop target."""
        del kwargs
        if self.knockdown_coil and not self.machine.switch_controller.is_active(self.config['switch'].name):
            self.knockdown_coil.pulse()

    def _update_state_from_switch(self):
        if self._in_ball_search:
            return

        if self.machine.switch_controller.is_active(
                self.config['switch'].name):
            self._down()
        else:
            self._up()

        self._update_banks()

    def _down(self):
        self.complete = True
        self.machine.events.post('drop_target_' + self.name + '_down')
        '''event: drop_target_(name)_down
        desc: The drop target with the (name) has just changed to the "down"
        state.'''

    def _up(self):
        self.complete = False
        self.machine.events.post('drop_target_' + self.name + '_up')
        '''event: drop_target_(name)_up
        desc: The drop target (name) has just changed to the "up" state.'''

    def _update_banks(self):
        for bank in self.banks:
            bank.member_target_change()

    def add_to_bank(self, bank):
        """Add this drop target to a drop target bank.

         This allows the bank to update its status based on state changes to this drop target.

        Args:
            bank: DropTargetBank object to add this drop target to.
        """
        self.banks.add(bank)

    def remove_from_bank(self, bank):
        """Remove the DropTarget from a bank.

        Args:
            bank: DropTargetBank object to remove
        """
        self.banks.remove(bank)

    def reset(self, **kwargs):
        """Reset this drop target.

        If this drop target is configured with a reset coil, then this method
        will pulse that coil. If not, then it checks to see if this drop target
        is part of a drop target bank, and if so, it calls the reset() method of
        the drop target bank.

        This method does not reset the target profile, however, the switch event
        handler should reset the target profile on its own when the drop target
        physically moves back to the up position.
        """
        del kwargs

        if self.reset_coil and self.machine.switch_controller.is_active(self.config['switch'].name):
            self.reset_coil.pulse()


class DropTargetBank(SystemWideDevice, ModeDevice):

    """A bank of drop targets in a pinball machine by grouping together multiple `DropTarget` class devices."""

    config_section = 'drop_target_banks'
    collection = 'drop_target_banks'
    class_label = 'drop_target_bank'

    def __init__(self, machine, name):
        """Initialise drop target bank."""
        super().__init__(machine, name)

        self.drop_targets = list()
        self.reset_coil = None
        self.reset_coils = set()
        self.complete = False
        self.down = 0
        self.up = 0

    def _initialize(self):
        self.drop_targets = self.config['drop_targets']
        self.reset_coil = self.config['reset_coil']
        self.reset_coils = self.config['reset_coils']

        for target in self.drop_targets:
            target.add_to_bank(self)

        self.member_target_change()

        if self.debug:
            self.log.debug('Drop Targets: %s', self.drop_targets)

    def reset(self, **kwargs):
        """Reset this bank of drop targets.

        This method has some intelligence to figure out what coil(s) it should
        fire. It builds up a set by looking at its own reset_coil and
        reset_coils settings, and also scanning through all the member drop
        targets and collecting their coils. Then it pulses each of them. (This
        coil list is a "set" which means it only sends a single pulse to each
        coil, even if each drop target is configured with its own coil.)
        """
        del kwargs
        if self.debug:
            self.log.debug('Resetting')

        # figure out all the coils we need to pulse
        coils = set()

        for drop_target in self.drop_targets:
            if drop_target.reset_coil:
                coils.add(drop_target.reset_coil)

        for coil in self.reset_coils:
            coils.add(coil)

        if self.reset_coil:
            coils.add(self.reset_coil)

        # now pulse them
        for coil in coils:

            if self.debug:
                self.log.debug('Pulsing reset coils: %s', coils)

            coil.pulse()

    def member_target_change(self):
        """A member drop target has changed state.

        This method causes this group to update its down and up counts and
        complete status.
        """
        self.down = 0
        self.up = 0

        for target in self.drop_targets:
            if target.complete:
                self.down += 1
            else:
                self.up += 1

        if self.debug:
            self.log.debug(
                'Member drop target status change: Up: %s, Down: %s,'
                ' Total: %s', self.up, self.down,
                len(self.drop_targets))

        if self.down == len(self.drop_targets):
            self._bank_down()
        elif not self.down:
            self._bank_up()
        else:
            self._bank_mixed()

    def _bank_down(self):
        self.complete = True
        if self.debug:
            self.log.debug('All targets are down')

        self.machine.events.post('drop_target_bank_' + self.name + '_down')
        '''event: drop_target_bank_(name)_down
        desc: Every drop target in the drop target bank called
        (name) is now in the "down" state. This event is
        only posted once, when all the drop targets are down.'''

    def _bank_up(self):
        self.complete = False
        if self.debug:
            self.log.debug('All targets are up')
        self.machine.events.post('drop_target_bank_' + self.name + '_up')
        '''event: drop_target_bank_(name)_up
        desc: Every drop target in the drop target bank called
        (name) is now in the "up" state. This event is
        only posted once, when all the drop targets are up.'''

    def _bank_mixed(self):
        self.complete = False
        self.machine.events.post('drop_target_bank_' + self.name + '_mixed',
                                 down=self.down)
        '''event: drop_target_bank_(name)_mixed
        desc: The drop targets in the drop target bank
        (name) are in a "mixed" state, meaning that they're
        not all down or not all up. This event is posted every time a member
        drop target changes but the overall bank is not not complete.'''

    def device_removed_from_mode(self, mode):
        """Remove targets which were added in this mode."""
        for target in self.drop_targets:
            target.remove_from_bank(self)
