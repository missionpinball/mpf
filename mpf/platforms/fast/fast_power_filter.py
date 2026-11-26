"""FAST Smart Power Filter Board (FP-PWR-0007) on a Neuron breakout port."""

from packaging import version

from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.fast.fast_exp_board import FastBreakoutBoard

# Channel order of IV: and of the bits in IF:. This is the column order of the
# EXP CP: command (HV 1, HV 2, Cab, BBox, Pfld, CPU).
CHANNELS = ('hv1', 'hv2', 'cabinet', 'backbox', 'playfield', 'cpu')
HV_CHANNELS = ('hv1', 'hv2')
ALL_FUSES_OK = (1 << len(CHANNELS)) - 1

# IV: returns raw accumulated ADC counts (10 bit, 1.5 V reference, 16 samples,
# 158k/4.02k divider), so volts = counts * factor. FAST plans to return actual
# volts in a later firmware, which is why the factor is looked up per firmware
# version. Unknown firmware: fuses are still read, voltages are not.
IV_VOLTS_PER_COUNT = {
    '0.10': 0.003690,
}

PASSTHROUGH_COMMANDS = ('IF:', 'IV:')
CONFIRM_READINGS = 2        # a state only changes after this many identical readings in a row
BACKOFF_AFTER_FAILURES = 3  # after this many unanswered queries in a row ...
BACKOFF_FACTOR = 10         # ... only every n-th poll is sent
FIRST_READ_WITHOUT_POLLING = 1.0  # seconds after boot for the single read when poll_interval is 0
# A voltage machine variable only follows a reading that is more than this far (in volts) from the
# published value. Rounding alone is not enough: ADC noise of about 0.1 V flips the rounded value
# back and forth (48.3/48.4) and posted a machine_var_ event on nearly every poll.
VOLTAGE_HYSTERESIS = 0.15

STATUS_UNKNOWN = 'unknown'
STATUS_OK = 'ok'
STATUS_FAULT = 'fault'
STATUS_NOT_RESPONDING = 'not_responding'


class FastPowerFilterBoard(FastBreakoutBoard):

    """A FAST Smart Power Filter Board, read through an EB: passthrough on the Neuron's EXP board.

    The board reports six supply voltages (IV:) and which of its six fused
    outputs carry voltage (IF:). Both are polled periodically, stored in machine
    variables and turned into events when a fuse blows, a voltage leaves its
    tolerance band or the board stops answering.
    """

    # pylint: disable-msg=too-many-instance-attributes
    __slots__ = ["settings", "voltages", "fuses", "status", "_volts_per_count", "_query_in_flight",
                 "_failures", "_skipped_polls", "_state", "_candidate", "_candidate_count", "_published"]

    def __init__(self, config, expansion_board):
        """Initialize the power filter board."""
        super().__init__(config, expansion_board)

        for other in self.platform.exp_breakout_boards.values():
            if isinstance(other, FastPowerFilterBoard):
                raise ConfigFileError(f"Only one {self.model} is supported, but {other} is already configured",
                                      4, self.log.name)

        self.settings = self.platform.machine.config_validator.validate_config(
            'fast_power_filter', config.get('power_filter') or dict())

        self.voltages = {channel: None for channel in CHANNELS}
        self.fuses = None  # bit mask from IF:, bit set = output has voltage
        self.status = STATUS_UNKNOWN
        self._volts_per_count = None
        self._query_in_flight = False
        self._failures = 0
        self._skipped_polls = 0
        self._state = dict()            # committed state per key, e.g. ('fuse', 'hv1') -> True
        self._candidate = dict()        # state seen in the last reading(s), not yet committed
        self._candidate_count = dict()
        self._published = dict()        # voltage machine variable as last set, per channel

    def __repr__(self):
        """Return representation of the power filter board."""
        return f"Power Filter Board {self.model} @{self.address} on {self.expansion_board}"

    def start_tasks(self):
        """Start polling the board. Called once by the EXP communicator on boot."""
        if not self.hw_verified:
            self._set_responding(False)
            return []

        self._volts_per_count = self._lookup_scale(self.firmware_version)
        if self._volts_per_count is None:
            self.log.warning("%s: firmware %s is unknown, IV: (voltages) will not be read. "
                             "Fuses are still monitored.", self, self.firmware_version)

        # The first read waits one interval, so it doesn't delay the commands MPF sends while starting up.
        clock = self.platform.machine.clock
        if not self.settings['poll_interval']:
            return [clock.schedule_once(self.poll, FIRST_READ_WITHOUT_POLLING)]

        return [clock.schedule_interval(self.poll, self.settings['poll_interval'] / 1000)]

    @staticmethod
    def _lookup_scale(firmware):
        if not firmware:
            return None
        for known_firmware, factor in IV_VOLTS_PER_COUNT.items():
            if version.parse(known_firmware) == version.parse(firmware):
                return factor
        return None

    def poll(self):
        """Queue one read of fuses and voltages, unless one is still in flight."""
        if self._query_in_flight:
            return

        if self._failures >= BACKOFF_AFTER_FAILURES:
            self._skipped_polls = (self._skipped_polls + 1) % BACKOFF_FACTOR
            if self._skipped_polls:
                return

        commands = PASSTHROUGH_COMMANDS if self._volts_per_count else ('IF:',)
        self._query_in_flight = True
        self.communicator.send_passthrough(self, commands, self._process_readings)

    def _process_readings(self, results):
        """Handle the replies of one passthrough session (None if the session failed)."""
        self._query_in_flight = False
        results = results or dict()

        fuses = self._parse_fuses(results.get('IF:'))
        raw = self._parse_voltages(results.get('IV:'))

        if fuses is None and raw is None:
            self._failures += 1
            self._set_responding(False)
            return

        self._failures = 0
        self._set_responding(True)

        if fuses is not None:
            self._update_fuses(fuses)

        if raw is not None and self._volts_per_count:
            self._update_voltages(raw)

        self._update_status()

    def _parse_fuses(self, payload):
        if payload is None:
            return None
        try:
            fuses = int(payload, 16)
        except ValueError:
            self.log.warning("%s: invalid IF: response '%s'", self, payload)
            return None
        if not 0 <= fuses <= ALL_FUSES_OK:
            self.log.warning("%s: invalid IF: response '%s'", self, payload)
            return None
        return fuses

    def _parse_voltages(self, payload):
        if payload is None:
            return None
        try:
            raw = [int(value, 16) for value in payload.split(',')]
        except ValueError:
            raw = []
        if len(raw) != len(CHANNELS):
            self.log.warning("%s: invalid IV: response '%s'", self, payload)
            return None
        return raw

    def _debounce(self, key, new_state):
        """Return (old_state, True) once new_state has been seen CONFIRM_READINGS times in a row."""
        if self._candidate.get(key) == new_state:
            self._candidate_count[key] += 1
        else:
            self._candidate[key] = new_state
            self._candidate_count[key] = 1

        old_state = self._state.get(key)
        if old_state != new_state and self._candidate_count[key] >= CONFIRM_READINGS:
            self._state[key] = new_state
            return old_state, True
        return old_state, False

    def _update_fuses(self, fuses):
        self.fuses = fuses
        self._set_var('fast_power_filter_fuses', fuses)
        '''machine_var: fast_power_filter_fuses

        desc: Fuse status of the FAST Smart Power Filter Board as a bit mask (bit 0 = hv1 ... bit 5 = cpu).
        A set bit means the output behind that fuse carries voltage. 63 means all fuses are ok.
        '''

        for bit, channel in enumerate(CHANNELS):
            fuse_ok = bool(fuses & (1 << bit))
            old_state, changed = self._debounce(('fuse', channel), fuse_ok)
            if not changed:
                continue

            self._set_var(f'fast_power_filter_{channel}_fuse_ok', int(fuse_ok))
            '''machine_var: fast_power_filter_(channel)_fuse_ok

            desc: 1 if the output behind this fuse of the FAST Smart Power Filter Board carries voltage,
            0 if it does not (fuse blown or supply missing). Channels: hv1, hv2, cabinet, backbox,
            playfield, cpu.
            '''

            if not fuse_ok:
                self.log.warning("%s: fuse for %s is blown or has no voltage (IF:%02X)", self, channel, fuses)
                self._add_technical_alert(f"Fuse {channel} blown")
                self.platform.machine.events.post('fast_power_filter_fuse_blown', channel=channel, fuses=fuses)
                '''event: fast_power_filter_fuse_blown

                desc: The output behind a fuse of the FAST Smart Power Filter Board lost its voltage,
                usually because the fuse is blown. Also posted at startup if a fuse is already blown.

                args:
                    channel: hv1, hv2, cabinet, backbox, playfield or cpu
                    fuses: The fuse bit mask (bit set = output has voltage)
                '''
            elif old_state is not None:
                self.log.info("%s: fuse for %s is ok again", self, channel)
                self.platform.machine.events.post('fast_power_filter_fuse_restored', channel=channel, fuses=fuses)
                '''event: fast_power_filter_fuse_restored

                desc: An output of the FAST Smart Power Filter Board has voltage again after
                fast_power_filter_fuse_blown was posted for it.

                args:
                    channel: hv1, hv2, cabinet, backbox, playfield or cpu
                    fuses: The fuse bit mask (bit set = output has voltage)
                '''

    def _limits(self, channel):
        nominal = self.settings['hv_nominal'] if channel in HV_CHANNELS else self.settings['lv_nominal']
        tolerance = nominal * self.settings['voltage_tolerance'] / 100
        return nominal - tolerance, nominal + tolerance

    def _update_voltages(self, raw):
        for channel, counts in zip(CHANNELS, raw):
            voltage = round(counts * self._volts_per_count, 2)
            self.voltages[channel] = voltage
            self._publish_voltage(channel, voltage)
            '''machine_var: fast_power_filter_(channel)_voltage

            desc: Supply voltage measured by the FAST Smart Power Filter Board, in volts, rounded to 0.1 V.
            It only follows a reading that differs by more than 0.15 V from the current value, so ADC
            noise doesn't post machine_var_ events on every poll.
            Channels: hv1, hv2 (48 V coil power), cabinet, backbox, playfield, cpu (12 V).
            '''

            low, high = self._limits(channel)
            voltage_ok = low <= voltage <= high
            old_state, changed = self._debounce(('voltage', channel), voltage_ok)
            if not changed:
                continue

            if not voltage_ok:
                self.log.warning("%s: %s is %.2f V, outside of %.1f-%.1f V", self, channel, voltage, low, high)
                self._add_technical_alert(f"Voltage {channel} {voltage:.1f} V")
                self.platform.machine.events.post('fast_power_filter_voltage_fault', channel=channel,
                                                  voltage=voltage, low=low, high=high)
                '''event: fast_power_filter_voltage_fault

                desc: A supply voltage measured by the FAST Smart Power Filter Board left its tolerance
                band (fast: exp_int: boards: <board>: breakouts: power_filter: voltage_tolerance).

                args:
                    channel: hv1, hv2, cabinet, backbox, playfield or cpu
                    voltage: The measured voltage
                    low: Lower limit in volts
                    high: Upper limit in volts
                '''
            elif old_state is not None:
                self.log.info("%s: %s is ok again (%.2f V)", self, channel, voltage)
                self.platform.machine.events.post('fast_power_filter_voltage_ok', channel=channel,
                                                  voltage=voltage, low=low, high=high)
                '''event: fast_power_filter_voltage_ok

                desc: A supply voltage of the FAST Smart Power Filter Board is back inside its tolerance
                band after fast_power_filter_voltage_fault was posted for it.

                args:
                    channel: hv1, hv2, cabinet, backbox, playfield or cpu
                    voltage: The measured voltage
                    low: Lower limit in volts
                    high: Upper limit in volts
                '''

    def _set_responding(self, responding):
        if not self.hw_verified:
            # not found at startup: report it once, never poll
            if self.status != STATUS_NOT_RESPONDING:
                self.status = STATUS_NOT_RESPONDING
                self._set_var('fast_power_filter_status', self.status)
                self._post_not_responding()
            return

        old_state, changed = self._debounce(('responding', None), responding)
        if not changed:
            return

        if not responding:
            self.log.warning("%s is not responding", self)
            self.status = STATUS_NOT_RESPONDING
            self._set_var('fast_power_filter_status', self.status)
            self._post_not_responding()
        elif old_state is not None:
            self.log.info("%s is responding again", self)
            self.platform.machine.events.post('fast_power_filter_responding')
            '''event: fast_power_filter_responding

            desc: The FAST Smart Power Filter Board answers again after
            fast_power_filter_not_responding was posted.
            '''

    def _post_not_responding(self):
        self._add_technical_alert("Power filter board not responding")
        self.platform.machine.events.post('fast_power_filter_not_responding')
        '''event: fast_power_filter_not_responding

        desc: The FAST Smart Power Filter Board did not answer at startup or stopped answering.
        Fuses and voltages are unknown until fast_power_filter_responding is posted.
        '''

    def _update_status(self):
        if self._state.get(('responding', None)) is False:
            return
        if not all(('fuse', channel) in self._state for channel in CHANNELS):
            return  # first readings not confirmed yet, status stays "unknown"
        faults = [key for key, state in self._state.items() if key[0] in ('fuse', 'voltage') and state is False]
        self.status = STATUS_FAULT if faults else STATUS_OK
        self._set_var('fast_power_filter_status', self.status)
        '''machine_var: fast_power_filter_status

        desc: Overall state of the FAST Smart Power Filter Board: "unknown" (not read yet), "ok",
        "fault" (a fuse is blown or a voltage is out of range) or "not_responding".
        '''

    def _publish_voltage(self, channel, voltage):
        """Set the voltage machine variable, rounded to 0.1 V and with hysteresis."""
        published = self._published.get(channel)
        if published is not None and abs(voltage - published) <= VOLTAGE_HYSTERESIS:
            return
        published = round(voltage, 1)
        self._published[channel] = published
        self._set_var(f'fast_power_filter_{channel}_voltage', published)

    def _set_var(self, name, value):
        self.platform.machine.variables.set_machine_var(name, value)

    def _add_technical_alert(self, issue):
        service = getattr(self.platform.machine, 'service', None)
        if service:
            service.add_technical_alert(self, issue)

    def get_description_string(self) -> str:
        """Return description string for mpf hardware scan."""
        if self.fuses is None:
            fuses = 'unknown'
        else:
            fuses = f'{self.fuses:02X}'
        voltages = ', '.join(f'{channel} {value:.2f}V' for channel, value in self.voltages.items()
                             if value is not None) or 'unknown'
        return (f"Power Filter Board: {self.model} @{self.address}, Firmware: {self.firmware_version}, "
                f"Status: {self.status}, Fuses: {fuses}, Voltages: {voltages}")
