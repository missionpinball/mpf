"""Stern Spike Platform."""
import asyncio

import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface, LightPlatformDirectFade

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.spike.spike_defines import SpikeNodebus
from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform


class SpikeSwitch(SwitchPlatformInterface):

    """A switch on a Stern Spike node board."""

    def __init__(self, config, platform):
        """Initialise switch."""
        super().__init__(config, config['number'])
        self.node, self.index = self.number.split("-")
        self.node = int(self.node)
        self.index = int(self.index)
        self.platform = platform


class SpikeLight(LightPlatformDirectFade):

    """A light on a Stern Spike node board."""

    def __init__(self, node, number, platform):
        """Initialise light."""
        super().__init__(platform.machine.clock.loop)
        self.node = node
        self.number = number
        self.platform = platform

    def get_max_fade_ms(self):
        """Return max fade ms."""
        return 199  # int(199 * 1.28) = 255

    def set_brightness_and_fade(self, brightness: float, fade_ms: int):
        """Set brightness of channel."""
        fade_time = int(fade_ms * 1.28)
        brightness = int(brightness * 255)
        if 0 > brightness > 255:
            raise AssertionError("Brightness out of bound.")
        if 0 > fade_time > 255:
            raise AssertionError("Fade time out of bound.")
        data = bytearray([fade_time, brightness])
        self.platform.send_cmd(self.node, SpikeNodebus.SetLed + self.number, data)


class SpikeDriver(DriverPlatformInterface):

    """A driver on a Stern Spike node board."""

    def __init__(self, config, number, platform):
        """Initialise driver on Stern Spike."""
        super().__init__(config, number)
        self.platform = platform
        self.node, self.index = number.split("-")
        self.node = int(self.node)
        self.index = int(self.index)
        self._enable_task = None

    def get_pulse_power(self):
        """Return pulse power."""
        if not self.config['pulse_power']:
            return 0xFF

        if 0 > self.config['pulse_power'] > 8:
            raise AssertionError("Pulse power has to be beween 0 and 8")

        return int(self.config['pulse_power'] * 32) - 1

    def get_hold_power(self):
        """Return hold power."""
        if self.config['hold_power'] and 0 >= self.config['hold_power'] > 8:
            raise AssertionError("Hold power has to be beween 0 and 7")

        if self.config['allow_enable'] and not self.config['hold_power']:
            return 0xFF

        if not self.config['hold_power']:
            raise AssertionError("Need hold_power or allow_enable.")

        if self.config['hold_power'] > 7 and not self.config['allow_enable']:
            raise AssertionError("hold_power 8 is invalid with allow_enable false")

        return int(self.config['hold_power'] * 32) - 1

    def get_pulse_ms(self):
        """Return initial pulse_ms."""
        if not self.config['pulse_ms']:
            return self.platform.machine.config['mpf']['default_pulse_ms']
        return self.config['pulse_ms']

    def _trigger(self, power1, duration1, power2, duration2):
        msg = bytearray([
            self.index,
            power1,
            duration1 & 0xFF,
            1 if duration1 & 0x100 else 0,
            power2,
            duration2 & 0xFF,
            1 if duration2 & 0x100 else 0,
            0,
            0
        ])
        self.platform.send_cmd(self.node, SpikeNodebus.CoilFireRelease, msg)

    def enable(self, coil):
        """Pulse and enable coil."""
        if self._enable_task:
            return

        # initial pulse
        power1 = self.get_pulse_power()
        duration1 = int(self.get_pulse_ms() * 1.28)

        if duration1 > 0x1FF:
            raise AssertionError("Initial pulse too long.")

        # then enable hold
        power2 = self.get_hold_power()
        duration2 = 0x1FF

        self._trigger(power1, duration1, power2, duration2)

        self._enable_task = self.platform.machine.clock.loop.create_task(self._enable(power2))
        self._enable_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _enable(self, power):
        while True:
            yield from asyncio.sleep(.25, loop=self.platform.machine.clock.loop)
            self._trigger(power, 0x1FF, power, 0x1FF)

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def pulse(self, coil, milliseconds):
        """Pulse coil for a certain time."""
        power1 = power2 = self.get_pulse_power()
        duration1 = int(milliseconds * 1.28)
        duration2 = duration1 - 0xFF if duration1 > 0x1FF else 0
        if duration2 > 0x1FF:
            raise AssertionError("Pulse ms too long.")

        self._trigger(power1, duration1, power2, duration2)

        return milliseconds

    def disable(self, coil):
        """Disable coil."""
        # cancel enable task
        if self._enable_task:
            self._enable_task.cancel()
            self._enable_task = None

        # disable coil
        self._trigger(0, 0, 0, 0)

    def get_board_name(self):
        """Return name for service mode."""
        return "Spike Node {}".format(self.node)


class SpikePlatform(SwitchPlatform, LightsPlatform, DriverPlatform):

    """Stern Spike Platform."""

    # pylint: disable-msg=too-many-arguments
    def _write_rule(self, node, enable_switch_index, disable_switch_index, coil_index, pulse_power, pulse_ms,
                    hold_power, can_cancel_pulse):
        """Write a hardware rule to Stern Spike."""
        pulse_value = int(pulse_ms * 1.28)
        second_coil_action = 6 if disable_switch_index else 0

        self.send_cmd(node, SpikeNodebus.CoilSetReflex, bytearray(
            [coil_index,
             pulse_power, pulse_value & 0xFF, (pulse_value & 0xFF00) >> 8,
             hold_power, 0x00, 0x00, 0x00, 0x00,
             0, 0, 0, 0, 0, 0, 0, 0,
             0x40 + enable_switch_index, 0x40 + disable_switch_index if disable_switch_index is not None else 0, 0,
             2, second_coil_action, 1 if can_cancel_pulse else 0]))

    @staticmethod
    def _check_coil_switch_combination(switch, coil):
        if switch.hw_switch.node != coil.hw_driver.node:
            raise AssertionError("Coil {} and Switch {} need to be on the same node to write a rule".format(
                coil, switch
            ))

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set pulse on hit rule on driver."""
        self._check_coil_switch_combination(enable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, None, coil.hw_driver.index,
                         coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(), 0, False)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and enable and relase rule on driver."""
        self._check_coil_switch_combination(enable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, None, coil.hw_driver.index,
                         coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(),
                         coil.hw_driver.get_hold_power(), True)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set pulse on hit and release rule to driver."""
        self._check_coil_switch_combination(enable_switch, coil)
        self._check_coil_switch_combination(disable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, disable_switch.hw_switch.index,
                         coil.hw_driver.index, coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(),
                         coil.hw_driver.get_hold_power(), True)

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver."""
        self._check_coil_switch_combination(enable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, None, coil.hw_driver.index,
                         coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(), 0, True)

    def clear_hw_rule(self, switch, coil):
        """Disable hardware rule for this coil."""
        del switch
        self.send_cmd(coil.hw_driver.node, SpikeNodebus.CoilSetReflex, bytearray(
            [coil.hw_driver.index, 0, 0, 0, 0, 0x00, 0x00, 0x00, 0x00,
             0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0,
             0, 0, 0]))

    def configure_driver(self, config):
        """Configure a driver on Stern Spike."""
        return SpikeDriver(config, config['number'], self)

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Return a single light."""
        return [
            {
                "number": number,
            }
        ]

    def configure_light(self, number, subtype, platform_settings) -> SpikeLight:
        """Configure a light on Stern Spike."""
        del platform_settings, subtype
        node, number = number.split("-")
        return SpikeLight(int(node), int(number), self)

    def configure_switch(self, config):
        """Configure switch on Stern Spike."""
        return SpikeSwitch(config, self)

    def get_hw_switch_states(self):
        """Return current switch states."""
        hw_states = dict()
        for node in self._nodes:
            curr_bit = 1
            for index in range(0, 64):
                hw_states[str(node) + '-' + str(index)] = (curr_bit & self._inputs[node]) == 0
                curr_bit <<= 1
        return hw_states

    def __init__(self, machine):
        """Initialise spike hardware platform."""
        super().__init__(machine)
        self.log = logging.getLogger('Spike')
        self.log.debug("Configuring Stern Spike hardware.")
        self._writer = None
        self._reader = None
        self._inputs = {}
        self.config = None
        self._poll_task = None

        self._nodes = None

    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config_validator.validate_config("spike", self.machine.config['spike'])

        port = self.config['port']
        baud = self.config['baud']
        self.debug = self.config['debug']
        self._nodes = self.config['nodes']

        if 0 not in self._nodes:
            raise AssertionError("Please include CPU node 0 in nodes for Spike.")

        self.machine.clock.loop.run_until_complete(self._connect_to_hardware(port, baud))

        self._poll_task = self.machine.clock.loop.create_task(self._poll())
        self._poll_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _connect_to_hardware(self, port, baud):
        self.log.info("Connecting to %s at %sbps", port, baud)

        connector = self.machine.clock.open_serial_connection(
            url=port, baudrate=baud, limit=0)
        self._reader, self._writer = yield from connector

        yield from self._initialize()

    def _update_switches(self, node):
        if node not in self._nodes:     # pragma: no cover
            self.log.warning("Cannot read node %s because it is not configured.", node)
            return

        new_inputs_str = yield from self._read_inputs(node)
        if not new_inputs_str:      # pragma: no cover
            self.log.info("Node: %s did not return any inputs.", node)
            return

        new_inputs = self._input_to_int(new_inputs_str)

        if self.debug:
            self.log.debug("Inputs node: %s State: %s Old: %s New: %s",
                           node, "".join(bin(b) + " " for b in new_inputs_str[0:8]), self._inputs[node], new_inputs)

        changes = self._inputs[node] ^ new_inputs
        if changes != 0:
            curr_bit = 1
            for index in range(0, 64):
                if (curr_bit & changes) != 0:
                    self.machine.switch_controller.process_switch_by_num(
                        state=(curr_bit & new_inputs) == 0,
                        num=str(node) + "-" + str(index),
                        platform=self)
                curr_bit <<= 1
        elif self.debug:    # pragma: no cover
            self.log.debug("Got input activity but inputs did not change.")

        self._inputs[node] = new_inputs

    @asyncio.coroutine
    def _poll(self):
        while True:
            self._send_raw(bytearray([0]))

            try:
                result = yield from asyncio.wait_for(self._read_raw(1), 0.1, loop=self.machine.clock.loop)
            except asyncio.TimeoutError:    # pragma: no cover
                self.log.warning("Spike watchdog expired.")
                continue

            ready_node = result[0]

            if 0 < ready_node <= 0x0F or ready_node == 0xF0:
                # valid node ids
                if ready_node == 0xF0:
                    # virtual cpu node returns 0xF0 instead of 0 to make it distinguishable
                    ready_node = 0
                yield from self._update_switches(ready_node)
            elif ready_node > 0:    # pragma: no cover
                # invalid node ids
                self.log.warning("Spike desynced.")
                # give it a break of 50ms
                yield from asyncio.sleep(.05, loop=self.machine.clock.loop)
                # clear buffer
                # pylint: disable-msg=protected-access
                self._reader._buffer = bytearray()
            else:
                # sleep only if spike is idle
                yield from asyncio.sleep(1 / self.config['poll_hz'], loop=self.machine.clock.loop)

    def stop(self):
        """Stop hardware and close connections."""
        if self._writer:
            # send ctrl+c to stop the mpf-spike-bridge
            self._writer.write(b'\x03')

        if self._poll_task:
            self._poll_task.cancel()
            try:
                self.machine.clock.loop.run_until_complete(self._poll_task)
            except asyncio.CancelledError:
                pass

        self._writer.close()

    @staticmethod
    def _done(future):  # pragma: no cover
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def _send_raw(self, data):
        if self.debug:
            self.log.debug("Sending: %s", "".join("0x%02x " % b for b in data))
        self._writer.write(("".join("%02x " % b for b in data).encode()))
        self._writer.write("\n\r".encode())

    @asyncio.coroutine
    def _read_raw(self, msg_len):
        if not msg_len:
            raise AssertionError("Cannot read 0 length")

        if self.debug:
            self.log.debug("Reading %s bytes", msg_len)

        data = yield from self._reader.readexactly(msg_len * 3)
        # if we got a space
        if data[0] == ' ':
            data = data[1:]
            data += yield from self._reader.readexactly(1)

        result = bytearray()
        if self.debug:
            self.log.debug("Data: %s", data)
        for i in range(msg_len):
            result.append(int(data[i * 3:(i * 3) + 2], 16))

        return result

    @staticmethod
    def _checksum(cmd_str):
        checksum = 0
        for i in cmd_str:
            checksum += i
        return (256 - (checksum % 256)) % 256

    @asyncio.coroutine
    def send_cmd_and_wait_for_response(self, node, cmd, data, response_len):
        """Send cmd and wait for response."""
        if node > 15:
            raise AssertionError("Node must be 0-15.")
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(response_len)
        self._send_raw(cmd_str)
        if response_len:
            try:
                response = yield from asyncio.wait_for(self._read_raw(response_len), 0.2, loop=self.machine.clock.loop)
            except asyncio.TimeoutError:    # pragma: no cover
                self.log.warning("Failed to read %s bytes from Spike", response_len)
                return False

            if self._checksum(response) != 0:   # pragma: no cover
                self.log.warning("Checksum mismatch for response: %s", "".join("%02x " % b for b in response))
                # we resync by flushing the input
                self._writer.transport.serial.reset_input_buffer()
                # pylint: disable-msg=protected-access
                self._reader._buffer = bytearray()
                return False

            return response

        return False

    def send_cmd(self, node, cmd, data):
        """Send cmd which does not require a response."""
        if node > 15:
            raise AssertionError("Node must be 0-15.")
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(0)
        self._send_raw(cmd_str)

    def _read_inputs(self, node):
        return self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetInputState, bytearray(), 10)

    @staticmethod
    def _input_to_int(state):
        if state is False:
            return 0

        result = 0
        for i in range(8):
            result += pow(256, i) * int(state[i])

        return result

    @asyncio.coroutine
    def _initialize(self):
        # send ctrl+c to stop whatever is running
        self._writer.write(b'\x03')
        # flush input
        self._writer.transport.serial.reset_input_buffer()
        # pylint: disable-msg=protected-access
        self._reader._buffer = bytearray()
        # start mpf-spike-bridge
        self._writer.write("/bin/bridge\r\n".encode())
        welcome_str = b'MPF Spike Bridge!\r\n'
        yield from asyncio.sleep(.1, loop=self.machine.clock.loop)
        data = yield from self._reader.read(100)
        if data[-len(welcome_str):] != welcome_str:
            raise AssertionError("Expected '{}' got '{}'".format(welcome_str, data[:len(welcome_str)]))

        self.send_cmd(0, SpikeNodebus.Reset, bytearray())
        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([34]))
        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([17]))

        for node in self._nodes:
            if node == 0:
                continue
            self.send_cmd(node, SpikeNodebus.SetTraffic, bytearray([16]))
            self.send_cmd(node, SpikeNodebus.SetTraffic, bytearray([32]))

        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([34]))

        yield from asyncio.sleep(.2, loop=self.machine.clock.loop)

        for node in self._nodes:
            if node == 0:
                continue
            fw_version = yield from self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetVersion, bytearray(), 12)
            if fw_version:
                self.log.debug("Node: %s Version: %s", node, "".join("0x%02x " % b for b in fw_version))
            yield from self.send_cmd_and_wait_for_response(node, SpikeNodebus.INIT_BOARD, bytearray(), 4)

        for node in self._nodes:
            initial_inputs = yield from self._read_inputs(node)
            self._inputs[node] = self._input_to_int(initial_inputs)

        for node in self._nodes:
            if node == 0:
                continue
            yield from self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)
            yield from self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetCoilCurrent, bytearray([0]), 12)

        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([17]))
        yield from asyncio.sleep(.1, loop=self.machine.clock.loop)

        for node in self._nodes:
            if node == 0:
                continue
            yield from self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)
