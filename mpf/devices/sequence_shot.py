"""A shot in MPF."""
import asyncio
import uuid
from collections import namedtuple
from typing import List, Dict, Set

import mpf.core.delays
from mpf.core.mode import Mode
from mpf.core.player import Player
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice

ActiveSequence = namedtuple("ActiveSequence", ["id", "current_position_index", "next_event"])


class SequenceShot(SystemWideDevice, ModeDevice):

    """A device which represents a sequence shot."""

    config_section = 'sequence_shots'
    collection = 'sequence_shots'
    class_label = 'sequence_shot'

    __slots__ = ["delay", "active_sequences", "active_delays", "_sequence_events", "_delay_events"]

    def __init__(self, machine, name):
        """Initialise sequence shot."""
        super().__init__(machine, name)

        self.delay = mpf.core.delays.DelayManager(self.machine.delayRegistry)
        self.active_sequences = list()  # type: List[ActiveSequence]
        self.active_delays = set()      # type: Set[str]

        self._sequence_events = []      # type: List[str]
        self._delay_events = {}         # type: Dict[str, int]

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return True

    @asyncio.coroutine
    def device_added_system_wide(self):
        """Register switch handlers on load."""
        yield from super().device_added_system_wide()
        self._register_handlers()

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Register switch handlers on mode start."""
        super().device_loaded_in_mode(mode, player)
        self._register_handlers()

    def device_removed_from_mode(self, mode):
        """Unregister switch handlers on mode end."""
        del mode
        self._remove_handlers()
        self._reset_all_sequences()
        self.delay.clear()

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        if self.config['switch_sequence'] and self.config['event_sequence']:
            raise AssertionError("Sequence shot {} only supports switch_sequence or event_sequence".format(self.name))

        self._sequence_events = self.config['event_sequence']

        for switch in self.config['switch_sequence']:
            self._sequence_events.append(self.machine.switch_controller.get_active_event_for_switch(switch.name))

    def _register_handlers(self):
        for event in set(self._sequence_events):
            self.machine.events.add_handler(event, self._sequence_advance, event_name=event)

        for switch in self.config['cancel_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch.name, self.cancel, 1)

        for switch, ms in list(self.config['delay_switch_list'].items()):
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._delay_switch_hit, 1, callback_kwargs={"name": switch.name, "ms": ms})

        for event, ms in list(self.config['delay_event_list'].items()):
            self.machine.events.add_handler(event, self._delay_switch_hit, name=event, ms=ms)

    def _remove_handlers(self):
        self.machine.events.remove_handler(self._sequence_advance)
        self.machine.events.remove_handler(self._delay_switch_hit)

        for switch in self.config['cancel_switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self.cancel, 1)

        for switch in list(self.config['delay_switch_list'].keys()):
            self.machine.switch_controller.remove_switch_handler(
                switch.name, self._delay_switch_hit, 1)

    def _sequence_advance(self, event_name, **kwargs):
        # Since we can track multiple simulatenous sequences (e.g. two balls
        # going into an orbit in a row), we first have to see whether this
        # switch is starting a new sequence or continuing an existing one
        del kwargs

        # mark playfield active
        if self.config['playfield']:
            self.config['playfield'].mark_playfield_active_from_device_action()

        self.debug_log("Sequence advance: %s", event_name)

        if event_name == self._sequence_events[0]:
            if len(self._sequence_events) > 1:
                # start a new sequence
                self._start_new_sequence()
            else:
                # if it only has one step it will finish right away
                self._completed()
        else:
            # Get the seq_id of the first sequence this switch is next for.
            # This is not a loop because we only want to advance 1 sequence
            seq = next((x for x in self.active_sequences if
                        x.next_event == event_name), None)

            if seq:
                # advance this sequence
                self._advance_sequence(seq)

    def _start_new_sequence(self):
        # If the sequence hasn't started, make sure we're not within the
        # delay_switch hit window

        if self.active_delays:
            self.debug_log("There's a delay timer in effect from %s. Sequence will not be started.",
                           self.active_delays)
            return

        # create a new sequence
        seq_id = uuid.uuid4()
        next_event = self._sequence_events[1]

        self.debug_log("Setting up a new sequence. Next: %s", next_event)

        self.active_sequences.append(ActiveSequence(seq_id, 0, next_event))

        # if this sequence has a time limit, set that up
        if self.config['sequence_timeout']:
            self.debug_log("Setting up a sequence timer for %sms",
                           self.config['sequence_timeout'])

            self.delay.reset(name=seq_id,
                             ms=self.config['sequence_timeout'],
                             callback=self._sequence_timeout,
                             seq_id=seq_id)

    def _advance_sequence(self, sequence: ActiveSequence):
        # Remove this sequence from the list
        self.active_sequences.remove(sequence)

        if sequence.current_position_index == (len(self._sequence_events) - 2):  # complete

            self.debug_log("Sequence complete!")

            self.delay.remove(sequence.id)
            self._completed()

        else:
            current_position_index = sequence.current_position_index + 1
            next_event = self._sequence_events[current_position_index + 1]

            self.debug_log("Advancing the sequence. Next: %s", next_event)

            self.active_sequences.append(ActiveSequence(sequence.id, current_position_index, next_event))

    def _completed(self):
        """Post sequence complete event."""
        self.machine.events.post("{}_hit".format(self.name))
        '''event: (sequence_shot)__hit
        desc: The sequence_shot called (sequence_shot) was just completed.
        '''

    def cancel(self, **kwargs):
        """Reset all sequences."""
        del kwargs
        self._reset_all_sequences()

    def _reset_all_sequences(self):
        seq_ids = [x.id for x in self.active_sequences]

        for seq_id in seq_ids:
            self.delay.remove(seq_id)

        self.active_sequences = list()

    def _delay_switch_hit(self, name, ms, **kwargs):
        del kwargs
        self.delay.reset(name=name + '_delay_timer',
                         ms=ms,
                         callback=self._release_delay,
                         delay_name=name)

        self.active_delays.add(name)

    def _release_delay(self, delay_name):
        self.active_delays.remove(delay_name)

    def _sequence_timeout(self, seq_id):
        """Sequence timeouted."""
        self.debug_log("Sequence %s timeouted", seq_id)

        self.active_sequences = [x for x in self.active_sequences
                                 if x[0] != seq_id]

        self.machine.events.post("{}_timeout".format(self.name))
