"""Stern Spike Platform."""
import asyncio

import logging

from mpf.platforms.spike.spike_defines import SpikeNodebus
from mpf.core.platform import SwitchPlatform, DriverPlatform


class SpikePlatform(SwitchPlatform, DriverPlatform):

    "Stern Spike Platform."


    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        pass

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        pass

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        pass

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        pass

    def clear_hw_rule(self, switch, coil):
        pass

    def configure_driver(self, config):
        pass
        self._send_cmd(10, SpikeNodebus.CoilTrigger, bytearray([0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))

    def configure_switch(self, config):
        pass

    def get_hw_switch_states(self):
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

        # TODO: where do we get those from? maybe just iterate all of them?
        self._nodes = [1, 8, 9, 10, 11]

    def initialize(self):
        # TODO: read from config
        port = "/dev/ttyUSB0"
        baud = 115200

        self.machine.clock.loop.run_until_complete(self._connect_to_hardware(port, baud))

        self._poll_task = self.machine.clock.loop.create_task(self._poll_task())
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
        new_inputs = self._read_inputs(node)
        if not new_inputs:
            self.log.info("Node: %s did not return any inputs.", node)
            return
        if self.debug:
            self.log.debug("Inputs node: %s State: %s", node, "".join(bin(b) + " " for b in new_inputs[0:8]))

        changes = self._inputs[node] ^ new_inputs
        if changes != 0:
            curr_bit = 1
            for index in range(0, 64):
                if (curr_bit & changes) != 0:
                    self.machine.switch_controller.process_switch_by_num(
                        state=(curr_bit & new_inputs) == 0,
                        num=str(node) + str(index),
                        platform=self)
                curr_bit <<= 1

        self._inputs[node] = new_inputs


    @asyncio.coroutine
    def _poll_task(self):
        while True:
            self._send_raw(bytearray([0]))

            ready_node = ord((yield from self._reader.read(1))[0])

            if ready_node > 0:
                self._update_switches(ready_node)

            yield from asyncio.sleep(.001, loop=self.machine.clock.loop)

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
    def _read_raw(self, len):
        if not len:
            raise AssertionError("Cannot read 0 length")

        if self.debug:
            self.log.debug("Reading %s bytes", len)

        data = yield from self._reader.readexactly(len * 3)
        # if we got a space
        if data[0] == ' ':
            data = data[1:]
            data += yield from self._reader.readexactly(1)

        result = bytearray()
        if self.debug:
            self.log.debug("Data: %s", data)
        for i in range(len):
            result.append(int(data[i*3:(i*3) + 2], 16))

        return result

    def _checksum(self, cmd_str):
        checksum = 0
        for i in cmd_str:
            checksum += i
        return (256 - (checksum % 256)) % 256

    @asyncio.coroutine
    def _send_cmd_and_wait_for_response(self, node, cmd, data, response_len = 0):
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(response_len)
        self._send_raw(cmd_str)
        if response_len:
            response = yield from self._read_raw(response_len)
            if self._checksum(response) != 0:
                self.log.info("Checksum mismatch for response: %s", response)
                return False

            return response

        return False

    def _send_cmd(self, node, cmd, data):
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(0)
        self._send_raw(cmd_str)

    def _read_inputs(self, node):
        return self._send_cmd_and_wait_for_response(node, SpikeNodebus.GetInputState, bytearray(), 10)

    @asyncio.coroutine
    def _initialize(self):
        self._send_cmd(0, SpikeNodebus.Reset, bytearray())
        self._send_cmd(0, SpikeNodebus.SetTraffic, bytearray([34]))
        self._send_cmd(0, SpikeNodebus.SetTraffic, bytearray([17]))

        for node in self._nodes:
            self._send_cmd(node, SpikeNodebus.SetTraffic, bytearray([16]))
            self._send_cmd(node, SpikeNodebus.SetTraffic, bytearray([32]))

        self._send_cmd(0, SpikeNodebus.SetTraffic, bytearray([34]))

        yield from asyncio.sleep(.5, loop=self.machine.clock.loop)

        for node in self._nodes:
            # TODO: why does spike do this 6 times?
            fw_version = yield from self._send_cmd_and_wait_for_response(node, SpikeNodebus.GetVersion, bytearray(), 12)
            if fw_version:
                self.log.debug("Node: %s Version: %s", node, "".join("0x%02x " % b for b in fw_version))
            yield from self._send_cmd_and_wait_for_response(node, SpikeNodebus.INIT_BOARD, bytearray(), 4)

        for node in self._nodes:
            self._inputs[node] = yield from self._read_inputs(node)

        for node in self._nodes:
            yield from self._send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)
            yield from self._send_cmd_and_wait_for_response(node, SpikeNodebus.GetCoilCurrent, bytearray([0]), 12)

        self._send_cmd(0, SpikeNodebus.SetTraffic, bytearray([17]))
        yield from asyncio.sleep(.1, loop=self.machine.clock.loop)

        for node in self._nodes:
            yield from self._send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)


