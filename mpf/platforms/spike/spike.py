"""Stern Spike Platform."""
import asyncio

import logging

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface

from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.spike.spike_defines import SpikeNodebus
from mpf.core.platform import SwitchPlatform, MatrixLightsPlatform, DriverPlatform


class SpikeSwitch(SwitchPlatformInterface):

    """A switch on a Stern Spike node board."""

    def __init__(self, config, platform):
        """Initialise switch."""
        super().__init__(config, config['number'])
        self.platform = platform


class SpikeLight(MatrixLightPlatformInterface):

    """A light on a Stern Spike node board."""

    def __init__(self, node, number, platform):
        """Initialise switch."""
        self.node = node
        self.number = number
        self.platform = platform

    def on(self, brightness=255):
        """Set brightness of channel."""
        fade_time = 30
        data = bytearray([fade_time, brightness])
        self.platform.send_cmd(self.node, SpikeNodebus.SetLed + self.number, data)


class SpikeDriver(DriverPlatformInterface):

    """A driver on a Stern Spike node board."""

    def __init__(self, config, number, platform):
        super().__init__(config, number)
        self.platform = platform
        self.node, self.index = number.split("-")
        self.node = int(self.node)
        self.index = int(self.index)

    def _get_pulse_power(self):
        # TODO: implement pulse_power
        return 0xFF

    def _get_hold_power(self):
        # TODO: implement hold_power
        return 0xFF

    def _get_initial_pulse_ms(self):
        # TODO: implement this
        return 10

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
        self.platform.send_cmd(self.node, SpikeNodebus.CoilTrigger, msg)

    def enable(self, coil):
        """Pulse and enable coil."""
        # initial pulse
        power1 = self._get_pulse_power()
        duration1 = self._get_initial_pulse_ms() * 1.28

        if duration1 > 0x1FF:
            raise AssertionError("Initial pulse too long.")

        # then enable hold
        power2 = self._get_hold_power()
        duration2 = 0x1FF

        self._trigger(power1, duration1, power2, duration2)

        self._enable_task = self.platform.machine.clock.loop.create_task(self._enable())
        self._enable_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _enable(self, power):
        while True:
            yield from asyncio.sleep(.25, loop=self.platform.machine.clock.loop)
            self._trigger(power, 0x1FF, power, 0x1FF)

    def _done(self, future):
        future.result()

    def pulse(self, coil, milliseconds):
        """Pulse coil for a certain time."""
        power1 = power2 = self._get_pulse_power()
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


class SpikePlatform(SwitchPlatform, MatrixLightsPlatform, DriverPlatform):

    """Stern Spike Platform."""

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        pass

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        pass

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        pass

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        pass

    def clear_hw_rule(self, switch, coil):
        pass

    def configure_driver(self, config):
        return SpikeDriver(config, config['number'], self)

    def configure_matrixlight(self, config):
        node, number = config['number'].split("-")
        return SpikeLight(int(node), int(number), self)

    def _disable_driver(self):
        self.send_cmd(10, SpikeNodebus.CoilTrigger, bytearray([0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))

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

        # TODO: where do we get those from? maybe just iterate all of them?
        self._nodes = [0, 1, 8, 9, 10, 11]

    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config_validator.validate_config("spike", self.machine.config['spike'])

        port = self.config['port']
        baud = self.config['baud']
        self.debug = self.config['debug']

        self.machine.clock.loop.run_until_complete(self._connect_to_hardware(port, baud))

        self._poll_task = self.machine.clock.loop.create_task(self._poll())
        self._poll_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _connect_to_hardware(self, port, baud):
        self.log.info("Connecting to %s at %sbps", port, baud)

        connector = self.machine.clock.open_serial_connection(
            url=port, baudrate=baud, limit=0)
        self._reader, self._writer = yield from connector

        # read everything which is sitting in the serial
        self._writer.transport.serial.reset_input_buffer()

        yield from self._initialize()

    def _update_switches(self, node):
        new_inputs_str = yield from self._read_inputs(node)
        if not new_inputs_str:
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
        elif self.debug:
            self.log.debug("Got input activity but inputs did not change.")

        self._inputs[node] = new_inputs

    @asyncio.coroutine
    def _poll(self):
        while True:
            self._send_raw(bytearray([0]))

            result = yield from self._read_raw(1)
            ready_node = result[0]

            if ready_node > 0:
                # virtual cpu node returns 0xF0 instead of 0 to make it distinguishable
                if ready_node == 0xF0:
                    ready_node = 0
                yield from self._update_switches(ready_node)

            yield from asyncio.sleep(.5, loop=self.machine.clock.loop)

    def stop(self):
        """Stop hardware and close connections."""
        if self._poll_task:
            self._poll_task.cancel()

        self._writer.close()

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    def _send_raw(self, data):
        if self.debug:
            self.log.debug("Sending: %s", "".join("0x%02x " % b for b in data))
        self._writer.write(("".join("%02x " % b for b in data).encode()))
        self._writer.write("\n\r".encode())

    def _set_backbox_light(self, brightness):
        pass
        # TODO: understand NODEBUS_SetBackboxLight, NODEBUS_VAPower, NODEBUS_SetPower
        # all message 0 with some parameters
        # 00 brightness brigness 2

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
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(response_len)
        self._send_raw(cmd_str)
        if response_len:
            # TODO: timeout
            response = yield from self._read_raw(response_len)
            if self._checksum(response) != 0:
                self.log.info("Checksum mismatch for response: %s", "".join("%02x " % b for b in response))
                # we resync by flushing the input
                # TODO: look for resync header
                self._writer.transport.serial.reset_input_buffer()
                return False

            return response

        return False

    def send_cmd(self, node, cmd, data):
        """Send cmd which does not require a response."""
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
        self.send_cmd(0, SpikeNodebus.Reset, bytearray())
        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([34]))
        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([17]))

        for node in self._nodes:
            if node == 0:
                continue
            self.send_cmd(node, SpikeNodebus.SetTraffic, bytearray([16]))
            self.send_cmd(node, SpikeNodebus.SetTraffic, bytearray([32]))

        self.send_cmd(0, SpikeNodebus.SetTraffic, bytearray([34]))

        yield from asyncio.sleep(.01, loop=self.machine.clock.loop)

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
