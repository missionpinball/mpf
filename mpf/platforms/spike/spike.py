"""Stern Spike Platform."""
import asyncio

import logging
import random
from typing import Generator

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface

from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.spike.spike_defines import SpikeNodebus
from mpf.core.platform import SwitchPlatform, MatrixLightsPlatform, DriverPlatform, DmdPlatform


class SpikeSwitch(SwitchPlatformInterface):

    """A switch on a Stern Spike node board."""

    def __init__(self, config, platform):
        """Initialise switch."""
        super().__init__(config, config['number'])
        self.node, self.index = self.number.split("-")
        self.node = int(self.node)
        self.index = int(self.index)
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
        fade_time = 12  # 10ms fade time by default
        data = bytearray([fade_time, brightness])
        self.platform.send_cmd_async(self.node, SpikeNodebus.SetLed + self.number, data)


class SpikeDMD(DmdPlatformInterface):

    """The DMD on the SPIKE system."""

    def __init__(self, platform):
        """Initialise DMD."""
        self.platform = platform
        self.data = None
        self.new_frame_event = asyncio.Event(loop=platform.machine.clock.loop)
        self.dmd_task = platform.machine.clock.loop.create_task(self._dmd_send())
        self.dmd_task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def update(self, data: bytes):
        """Remember the last frame data."""
        self.data = data
        self.new_frame_event.set()

    @asyncio.coroutine
    def _dmd_send(self):
        while True:
            yield from self.new_frame_event.wait()
            self.new_frame_event.clear()
            yield from self.send_update()

    @asyncio.coroutine
    def send_update(self):
        """Send update to platform."""
        if len(self.data) != 128 * 32:
            raise AssertionError("Invalid frame length for SPIKE. Should be 128*32 pixels.")
        frame1 = bytearray()
        frame2 = bytearray()
        frame3 = bytearray()
        frame4 = bytearray()
        # we build four frames for a 128*32 pixel display. one bit per pixel each = 512bytes
        for i in range(512):
            pixel1 = 0
            pixel2 = 0
            pixel3 = 0
            pixel4 = 0
            for p in range(8):
                pixel_data = self.data[i * 8 + p]
                pixel1 += 1 if pixel_data & 0x01 else 0
                pixel2 += 1 if pixel_data & 0x02 else 0
                pixel3 += 1 if pixel_data & 0x04 else 0
                pixel4 += 1 if pixel_data & 0x08 else 0
                pixel1 *= 2
                pixel2 *= 2
                pixel3 *= 2
                pixel4 *= 2

            frame1.append(int(pixel1 / 2))
            frame2.append(int(pixel2 / 2))
            frame3.append(int(pixel3 / 2))
            frame4.append(int(pixel4 / 2))
        yield from self.platform.send_cmd_raw(bytes([0x80, 0x00, 0x90]) + bytes(frame1) + bytes(frame2) +
                                              bytes(frame3) + bytes(frame4))

    def set_brightness(self, brightness: float):
        """Set brightness of the DMD."""
        # we do not yet know how that works in SPIKE
        pass


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
        self.platform.send_cmd_async(self.node, SpikeNodebus.CoilFireRelease, msg)

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

# pylint: disable-msg=too-many-arguments
class SpikePlatform(SwitchPlatform, MatrixLightsPlatform, DriverPlatform, DmdPlatform):

    """Stern Spike Platform."""

    # pylint: disable-msg=too-many-arguments
    def _write_rule(self, node, enable_switch_index, disable_switch_index, coil_index, pulse_power, pulse_ms,
                    hold_power, param1, param2, param3):
        """Write a hardware rule to Stern Spike.

        We do not yet understand param1, param2 and param3:
        param1 == 2 -> second switch (eos switch)
        param2 == 1 -> ??
        param2 == 6 -> ??
        param3 == 5 -> allow enable
        """
        pulse_value = int(pulse_ms * 1.28)

        self.send_cmd_async(node, SpikeNodebus.CoilSetReflex, bytearray(
            [coil_index,
             pulse_power, pulse_value & 0xFF, (pulse_value & 0xFF00) >> 8,
             hold_power, 0x00, 0x00, 0x00, 0x00,
             0, 0, 0, 0, 0, 0, 0, 0,
             0x40 + enable_switch_index, 0x40 + disable_switch_index if disable_switch_index is not None else 0, 0,
             param1, param2, param3]))

    @staticmethod
    def _check_coil_switch_combination(switch, coil):
        if switch.hw_switch.node != coil.hw_driver.node:
            raise AssertionError("Coil {} and Switch {} need to be on the same node to write a rule".format(
                coil, switch
            ))

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set pulse on hit rule on driver.

        This is mostly used for popbumpers. Example from WWE:
        Type: 8 Cmd: 65 Node: 9 Msg: 0x00 0xa6 0x28 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x14 0x00 0x00 0x00 0x38
        0x00 0x40 0x00 0x00 0x00 0x00 0x00 Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, None, coil.hw_driver.index,
                         coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(), 0, 0, 0, 0)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and enable and relase rule on driver.

        Used for single coil flippers. Examples from WWE:
        Dual-wound flipper hold coil:
        Type: 8 Cmd: 65 Node: 8 Msg: 0x02 0xff 0x46 0x01 0xff 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x3a
        0x00 0x42 0x40 0x00 0x00 0x01 0x00  Len: 25

        Ring Slings (different flags):
        Type: 8 Cmd: 65 Node: 10 Msg: 0x00 0xff 0x19 0x00 0x14 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x80
        0x00 0x4a 0x40 0x00 0x00 0x06 0x05  Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, None, coil.hw_driver.index,
                         coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(),
                         coil.hw_driver.get_hold_power(), 0, 6, 5)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set pulse on hit and release rule to driver.

        Used for high-power coil on dual-wound flippers. Example from WWE:
        Type: 8 Cmd: 65 Node: 8 Msg: 0x00 0xff 0x33 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x42 0x40 0x00 0x02 0x06 0x00  Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        self._check_coil_switch_combination(disable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, disable_switch.hw_switch.index,
                         coil.hw_driver.index, coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(),
                         coil.hw_driver.get_hold_power(), 2, 6, 0)

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver.

        I believe that param2 == 1 means that it will cancel the pulse when the switch is released.

        Used for high-power coils on dual-wound flippers. Example from WWE:
        Type: 8 Cmd: 65 Node: 8 Msg: 0x03 0xff 0x46 0x01 0xff 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x43 0x40 0x00 0x00 0x01 0x00  Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index, None, coil.hw_driver.index,
                         coil.hw_driver.get_pulse_power(), coil.hw_driver.get_pulse_ms(), 0, 0, 1, 0)

    def clear_hw_rule(self, switch, coil):
        """Disable hardware rule for this coil."""
        del switch
        self.send_cmd_async(coil.hw_driver.node, SpikeNodebus.CoilSetReflex, bytearray(
            [coil.hw_driver.index, 0, 0, 0, 0, 0x00, 0x00, 0x00, 0x00,
             0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0,
             0, 0, 0]))

    def configure_driver(self, config):
        """Configure a driver on Stern Spike."""
        return SpikeDriver(config, config['number'], self)

    def configure_matrixlight(self, config):
        """Configure a light on Stern Spike."""
        node, number = config['number'].split("-")
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
        self._sender_task = None
        self._send_key_task = None
        self.dmd = None

        self._nodes = None
        self._bus_busy = asyncio.Lock(loop=self.machine.clock.loop)
        self._cmd_queue = asyncio.Queue(loop=self.machine.clock.loop)

    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config_validator.validate_config("spike", self.machine.config['spike'])

        port = self.config['port']
        baud = self.config['baud']
        flow_control = self.config['flow_control']
        self.debug = self.config['debug']
        self._nodes = self.config['nodes']

        if 0 not in self._nodes:
            raise AssertionError("Please include CPU node 0 in nodes for Spike.")

        self.machine.clock.loop.run_until_complete(self._connect_to_hardware(port, baud, flow_control))

        self._poll_task = self.machine.clock.loop.create_task(self._poll())
        self._poll_task.add_done_callback(self._done)

        self._sender_task = self.machine.clock.loop.create_task(self._sender())
        self._sender_task.add_done_callback(self._done)

        if self.config['use_send_key']:
            self._send_key_task = self.machine.clock.loop.create_task(self._send_key())
            self._send_key_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _connect_to_hardware(self, port, baud, flow_control):
        self.log.info("Connecting to %s at %sbps", port, baud)

        connector = self.machine.clock.open_serial_connection(
            url=port, baudrate=baud, rtscts=flow_control)
        self._reader, self._writer = yield from connector
        self._writer.transport.set_write_buffer_limits(4096, 1024)

        yield from self._initialize()

    @asyncio.coroutine
    def _update_switches(self, node):
        if node not in self._nodes:
            self.log.warning("Cannot read node %s because it is not configured.", node)
            return False

        new_inputs_str = yield from self._read_inputs(node)
        if not new_inputs_str:
            self.log.info("Node: %s did not return any inputs.", node)
            return True

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

        return True

    @asyncio.coroutine
    def _sender(self):
        while True:
            cmd, wait_ms = yield from self._cmd_queue.get()
            with (yield from self._bus_busy):
                yield from self._send_raw(cmd)
                if wait_ms:
                    yield from self._send_raw(bytearray([1, wait_ms]))

    @asyncio.coroutine
    def _send_key(self):
        while True:
            for node in self._nodes:
                # do not send watchdog to cpu since it is a virtual node
                if node == 0:
                    continue

                # generate super secret "key"
                key = bytearray()
                for i in range(16):
                    key.append(random.randint(0, 255))

                # send SendKey message
                yield from self.send_cmd_sync(node, SpikeNodebus.SendKey, key)

                # wait one second
                yield from asyncio.sleep(1, loop=self.machine.clock.loop)

    @asyncio.coroutine
    def _poll(self):
        while True:
            with (yield from self._bus_busy):
                yield from self._send_raw(bytearray([0]))

                try:
                    result = yield from asyncio.wait_for(self._read_raw(1), 0.5, loop=self.machine.clock.loop)
                except asyncio.TimeoutError:    # pragma: no cover
                    self.log.warning("Spike watchdog expired.")
                    # clear buffer
                    # pylint: disable-msg=protected-access
                    self._reader._buffer = bytearray()
                    continue

            ready_node = result[0]

            if 0 < ready_node <= 0x0F or ready_node == 0xF0:
                # valid node ids
                if ready_node == 0xF0:
                    # virtual cpu node returns 0xF0 instead of 0 to make it distinguishable
                    ready_node = 0
                result = yield from self._update_switches(ready_node)
                if not result:
                    self.log.warning("Spike desynced during input.")
                    yield from asyncio.sleep(.05, loop=self.machine.clock.loop)
                    # clear buffer
                    # pylint: disable-msg=protected-access
                    self._reader._buffer = bytearray()
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
        if self._poll_task:
            self._poll_task.cancel()

        if self._sender_task:
            self._sender_task.cancel()
            try:
                self.machine.clock.loop.run_until_complete(self._sender_task)
            except asyncio.CancelledError:
                pass

        if self._send_key_task:
            self._send_key_task.cancel()
            try:
                self.machine.clock.loop.run_until_complete(self._send_key_task)
            except asyncio.CancelledError:
                pass

        if self._writer:
            # send ctrl+c to stop the mpf-spike-bridge
            self._writer.write(b'\x03reset\n')

        self._writer.close()

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def _send_raw(self, data):
        if self.debug:
            self.log.debug("Sending: %s", "".join("%02x " % b for b in data))
        for start in range(0, len(data), 256):
            block = data[start:start + 256]
            self._writer.write(("".join("%02x " % b for b in block).encode()))
            self._writer.write("\n\r".encode())
        yield from self._writer.drain()

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
    def send_cmd_and_wait_for_response(self, node, cmd, data, response_len) -> Generator[int, None, str]:
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
        with (yield from self._bus_busy):
            yield from self._send_raw(cmd_str)
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

    def _create_cmd_str(self, node, cmd, data):
        if node > 15:
            raise AssertionError("Node must be 0-15.")
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(0)
        return cmd_str

    @asyncio.coroutine
    def send_cmd_sync(self, node, cmd, data):
        """Send cmd which does not require a response."""
        cmd_str = self._create_cmd_str(node, cmd, data)
        if (cmd & 0xF0) == 0x80:
            # special case for LED updates
            wait_ms = self.config['wait_times'][0x80] if 0x80 in self.config['wait_times'] else 0
        else:
            wait_ms = self.config['wait_times'][cmd] if cmd in self.config['wait_times'] else 0
        with (yield from self._bus_busy):
            yield from self._send_raw(cmd_str)
            if wait_ms:
                yield from self._send_raw(bytearray([1, wait_ms]))

    @asyncio.coroutine
    def send_cmd_raw(self, data, wait_ms=0):
        """Send raw command."""
        with (yield from self._bus_busy):
            yield from self._send_raw(data)
            if wait_ms:
                yield from self._send_raw(bytearray([1, wait_ms]))

    def send_cmd_async(self, node, cmd, data):
        """Send cmd which does not require a response."""
        cmd_str = self._create_cmd_str(node, cmd, data)
        wait_ms = self.config['wait_times'][cmd] if cmd in self.config['wait_times'] else 0
        # queue command
        self._cmd_queue.put_nowait((cmd_str, wait_ms))

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

    def configure_dmd(self):
        """Configure a DMD."""
        if self.dmd:
            raise AssertionError("Can only configure dmd once.")
        self.dmd = SpikeDMD(self)
        return self.dmd

    @asyncio.coroutine
    def _initialize(self) -> None:
        # send ctrl+c to stop whatever is running
        self._writer.write(b'\x03reset\n')
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

        yield from self.send_cmd_sync(0, SpikeNodebus.Reset, bytearray())
        yield from self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([34]))
        yield from self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([17]))

        for node in self._nodes:
            if node == 0:
                continue
            yield from self.send_cmd_sync(node, SpikeNodebus.SetTraffic, bytearray([16]))
            yield from self.send_cmd_sync(node, SpikeNodebus.SetTraffic, bytearray([32]))

        yield from self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([34]))

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

        yield from self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([17]))
        yield from asyncio.sleep(.1, loop=self.machine.clock.loop)

        for node in self._nodes:
            if node == 0:
                continue
            yield from self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)
