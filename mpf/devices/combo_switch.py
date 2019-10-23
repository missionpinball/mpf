"""Contains the Combo Switch device class."""
from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice
from mpf.core.player import Player
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("state")
class ComboSwitch(SystemWideDevice, ModeDevice):

    """Combo Switch device."""

    config_section = 'combo_switches'
    collection = 'combo_switches'
    class_label = 'combo_switch'

    __slots__ = ["states", "_state", "_switches_1_active", "_switches_2_active", "delay"]

    def __init__(self, machine, name):
        """Initialize Combo Switch."""
        super().__init__(machine, name)
        self.states = ['inactive', 'both', 'one']
        self._state = 'inactive'
        self._switches_1_active = False
        self._switches_2_active = False

        self.delay = DelayManager(self.machine)

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Validate and parse config."""
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)

        for state in self.states:
            if not config['events_when_{}'.format(state)]:
                config['events_when_{}'.format(state)] = [
                    "{}_{}".format(self.name, state)]
        for state in ["switches_1", "switches_2"]:
            if not config['events_when_{}'.format(state)]:
                config['events_when_{}'.format(state)] = [
                    "{}_{}".format(self.name, state)]

        return config

    async def device_added_system_wide(self):
        """Add event handlers."""
        await super().device_added_system_wide()
        self._add_switch_handlers()

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Add event handlers."""
        self._add_switch_handlers()

    def _add_switch_handlers(self):
        if self.config['tag_1']:
            for tag in self.config['tag_1']:
                for switch in self.machine.switches.items_tagged(tag):
                    self.config['switches_1'].add(switch)

        if self.config['tag_2']:
            for tag in self.config['tag_2']:
                for switch in self.machine.switches.items_tagged(tag):
                    self.config['switches_2'].add(switch)

        self._register_switch_handlers()

    @property
    def state(self):
        """Return current state."""
        return self._state

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return True

    def device_removed_from_mode(self, mode):
        """Mode ended.

        Args:
            mode: mode which stopped
        """
        del mode

        self._remove_switch_handlers()
        self._kill_delays()

    def _register_switch_handlers(self):
        for switch in self.config['switches_1']:
            switch.add_handler(self._switch_1_went_active, state=1)
            switch.add_handler(self._switch_1_went_inactive, state=0)

        for switch in self.config['switches_2']:
            switch.add_handler(self._switch_2_went_active, state=1)
            switch.add_handler(self._switch_2_went_inactive, state=0)

    def _remove_switch_handlers(self):
        for switch in self.config['switches_1']:
            switch.remove_handler(self._switch_1_went_active, state=1)
            switch.remove_handler(self._switch_1_went_inactive, state=0)

        for switch in self.config['switches_2']:
            switch.remove_handler(self._switch_2_went_active, state=1)
            switch.remove_handler(self._switch_2_went_inactive, state=0)

    def _kill_delays(self):
        self.delay.clear()

    def _switch_1_went_active(self):
        self.debug_log('A switch from switches_1 just went active')
        self.delay.remove('switch_1_inactive')

        if self._switches_1_active:
            return

        if not self.config['hold_time']:
            self._activate_switches_1()
        else:
            self.delay.add_if_doesnt_exist(self.config['hold_time'],
                                           self._activate_switches_1,
                                           'switch_1_active')

    def _switch_2_went_active(self):
        self.debug_log('A switch from switches_2 just went active')
        self.delay.remove('switch_2_inactive')

        if self._switches_2_active:
            return

        if not self.config['hold_time']:
            self._activate_switches_2()
        else:
            self.delay.add_if_doesnt_exist(self.config['hold_time'],
                                           self._activate_switches_2,
                                           'switch_2_active')

    def _switch_1_went_inactive(self):
        self.debug_log('A switch from switches_1 just went inactive')
        for switch in self.config['switches_1']:
            if switch.state:
                # at least one switch is still active
                return

        self.delay.remove('switch_1_active')

        if not self.config['release_time']:
            self._release_switches_1()
        else:
            self.delay.add_if_doesnt_exist(self.config['release_time'],
                                           self._release_switches_1,
                                           'switch_1_inactive')

    def _switch_2_went_inactive(self):
        self.debug_log('A switch from switches_2 just went inactive')
        for switch in self.config['switches_2']:
            if switch.state:
                # at least one switch is still active
                return

        self.delay.remove('switch_2_active')

        if not self.config['release_time']:
            self._release_switches_2()
        else:
            self.delay.add_if_doesnt_exist(self.config['release_time'],
                                           self._release_switches_2,
                                           'switch_2_inactive')

    def _activate_switches_1(self):
        self.debug_log('Switches_1 has passed the hold time and is now '
                       'active')
        self._switches_1_active = self.machine.clock.get_time()
        self.delay.remove("switch_2_only")

        if self._switches_2_active:
            if (self.config['max_offset_time'] >= 0 and
                    (self._switches_1_active - self._switches_2_active >
                        self.config['max_offset_time'])):

                self.debug_log("Switches_2 is active, but the "
                               "max_offset_time=%s which is largest than when "
                               "a Switches_2 switch was first activated, so "
                               "the state will not switch to 'both'",
                               self.config['max_offset_time'])

                return

            self._switch_state('both')
        elif self.config['max_offset_time'] >= 0:
            self.delay.add_if_doesnt_exist(self.config['max_offset_time'] * 1000, self._post_only_one_active_event,
                                           "switch_1_only", number=1)

    def _activate_switches_2(self):
        self.debug_log('Switches_2 has passed the hold time and is now '
                       'active')
        self._switches_2_active = self.machine.clock.get_time()
        self.delay.remove("switch_1_only")

        if self._switches_1_active:
            if (self.config['max_offset_time'] >= 0 and
                    (self._switches_2_active - self._switches_1_active >
                        self.config['max_offset_time'])):
                self.debug_log("Switches_2 is active, but the "
                               "max_offset_time=%s which is largest than when "
                               "a Switches_2 switch was first activated, so "
                               "the state will not switch to 'both'",
                               self.config['max_offset_time'])
                return

            self._switch_state('both')
        elif self.config['max_offset_time'] >= 0:
            self.delay.add_if_doesnt_exist(self.config['max_offset_time'] * 1000, self._post_only_one_active_event,
                                           "switch_2_only", number=2)

    def _post_only_one_active_event(self, number):
        for event in self.config['events_when_switches_{}'.format(number)]:
            self.machine.events.post(event)

    def _release_switches_1(self):
        self.debug_log('Switches_1 has passed the release time and is now '
                       'releases')
        self._switches_1_active = None
        if self._switches_2_active and self._state == 'both':
            self._switch_state('one')
        elif self._state == 'one':
            self._switch_state('inactive')

    def _release_switches_2(self):
        self.debug_log('Switches_2 has passed the release time and is now '
                       'releases')
        self._switches_2_active = None
        if self._switches_1_active and self._state == 'both':
            self._switch_state('one')
        elif self._state == 'one':
            self._switch_state('inactive')

    def _switch_state(self, state):
        """Post events for current step."""
        if state not in self.states:
            raise ValueError("Received invalid state: {}".format(state))

        if state == self.state:
            return

        self._state = state
        self.debug_log("New State: %s", state)

        for event in self.config['events_when_{}'.format(state)]:
            self.machine.events.post(event)
            '''event: (combo_switch)_(state)
            desc: Combo switch (name) changed to state (state).

            Note that these events can be overridden in a combo switch's
            config.

            Valid states are: *inactive*, *both*, or *one*.

            ..rubric:: both

            A switch from group 1 and group 2 are both active at the
            same time, having been pressed within the ``max_offset_time:`` and
            being active for at least the ``hold_time:``.

            ..rubric:: one

            Either switch 1 or switch 2 has been released for at
            least the ``release_time:`` but the other switch is still active.

            ..rubric:: switches_1

            Only switches_1 is active. max_offset_time has passed and this hit
            cannot become both later on. Only emmited when ``max_offset_time:``
            is defined.

            ..rubric:: switches_2

            Only switches_2 is active. max_offset_time has passed and this hit
            cannot become both later on. Only emmited when ``max_offset_time:``
            is defined.

            ..rubric:: inactive

            Both switches are inactive.

            '''

            '''event: flipper_cancel

            desc: Posted when both flipper buttons are hit at the same time,
            useful as a "cancel" event for shows, the bonus mode, etc.

            Note that in order for this event to work, you have to add
            ``left_flipper`` as a tag to the switch for your left flipper,
            and ``right_flipper`` to your right flipper.

            See :doc:`/config/combo_switches` for details.
            '''
