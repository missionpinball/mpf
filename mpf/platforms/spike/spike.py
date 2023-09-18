# pylint: disable-msg=too-many-lines
"""Stern Spike Platform."""
import asyncio

import random
from typing import Optional, Union

from mpf.platforms.base_serial_communicator import HEX_FORMAT
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface
from mpf.core.platform_batch_light_system import PlatformBatchLight, PlatformBatchLightSystem
from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.spike.spike_defines import SpikeNodebus
from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, DmdPlatform, StepperPlatform, RepulseSettings

from mpf.core.utility_functions import Util

SPIKE_NODE_FORMAT = "Spike Node {}"


class SpikeSwitch(SwitchPlatformInterface):

    """A switch on a Stern Spike node board."""

    __slots__ = ["node", "index", "platform_config", "_last_debounce"]

    def __init__(self, config, number, platform, platform_config):
        """initialize switch."""
        super().__init__(config, number, platform)
        self.node, self.index = self.number.split("-")
        self.node = int(self.node)
        self.index = int(self.index)
        self.platform_config = platform_config
        self._last_debounce = None

    def configure_debounce_and_recycle(self, enable_debounce, invert_switch, enable_recycle):
        """Configure debounce time."""
        if self.platform.node_firmware_version[self.node] < 0x2800:
            return

        # the logic here is a bit tricky because we use debounce to implement recycle as well
        # if recycle is enabled we will always debounce the switch closing (or opening if inverted)
        # this kind of emulates recycling

        if enable_debounce and (not invert_switch or not enable_recycle):
            if self.platform_config["debounce_open"]:
                debounce_open_ms = self.platform_config["debounce_open"]
            else:
                debounce_open_ms = self.platform.config["default_debounce_open"]
        else:
            debounce_open_ms = 2

        if enable_debounce and (invert_switch or not enable_recycle):
            if self.platform_config["debounce_close"]:
                debounce_close_ms = self.platform_config["debounce_close"]
            else:
                debounce_close_ms = self.platform.config["default_debounce_close"]
        else:
            debounce_close_ms = 2

        new_debounce = (debounce_open_ms, debounce_close_ms)
        if new_debounce == self._last_debounce:
            return

        self._last_debounce = new_debounce

        debounce_open_value = int(debounce_open_ms * self.platform.ticks_per_sec[self.node] / 1000)
        debounce_closed_value = int(debounce_close_ms * self.platform.ticks_per_sec[self.node] / 1000)
        if debounce_open_value > 0xfe:
            debounce_open_value = 0xfe
        if debounce_closed_value > 0xfe:
            debounce_closed_value = 0xfe

        self.platform.log.debug("Set debounce open: %s close: %s (about %sms and %sms) for switch %s",
                                debounce_open_value, debounce_closed_value, debounce_open_value,
                                debounce_closed_value, self.number)
        self.platform.send_cmd_async(self.node, SpikeNodebus.ConfigInput, bytearray([self.index,
                                                                                     debounce_open_value,
                                                                                     debounce_closed_value]))

    def get_board_name(self):
        """Return name for service mode."""
        return SPIKE_NODE_FORMAT.format(self.node)


class SpikeBacklight(LightPlatformSoftwareFade):

    """The backlight on the CPU node."""

    __slots__ = ["platform"]

    def __init__(self, number, platform, loop, fade_interval_ms):
        """initialize backlight."""
        super().__init__(number, loop, fade_interval_ms)
        self.platform = platform        # type: SpikePlatform

    def set_brightness(self, brightness: float):
        """Set brightness."""
        # we use the Spike 2 command. it will be intercepted in the mpf-spike bridge for Spike 1
        brightness_u16 = int(brightness * 65535)
        self.platform.send_cmd_raw_async([SpikeNodebus.SetBackboxLight, 2,
                                          brightness_u16 >> 8, brightness_u16 & 0xFF,
                                          0])

    def get_board_name(self):
        """Return name for service mode."""
        return "Spike Node 0"

    def is_successor_of(self, other):
        """There can only be one backlight."""
        raise AssertionError("Not possible for backlight.")

    def get_successor_number(self):
        """There can only be one backlight."""
        raise AssertionError("Not possible for backlight.")

    def __lt__(self, other):
        """There can only be one backlight."""
        return self.number < other.number


class SpikeLight(PlatformBatchLight):

    """A light on a Stern Spike node board."""

    __slots__ = ["node", "index", "platform", "_max_fade"]

    def __init__(self, number, platform, light_system):
        """initialize light."""
        super().__init__(number, light_system)
        node, index = number.split("-")
        self.node = int(node)
        self.index = int(index)
        self.platform = platform
        self._max_fade = None

    def get_max_fade_ms(self):
        """Return max fade ms."""
        if self.node == 0:
            return 0
        if self._max_fade is None:
            # calculate max fade time. 255 is reserved so 254 is the max value
            self._max_fade = int(254 * 1000 / self.platform.ticks_per_sec[self.node])
        return self._max_fade

    def get_board_name(self):
        """Return name for service mode."""
        return SPIKE_NODE_FORMAT.format(self.node)

    def is_successor_of(self, other):
        """Return true if the other light has the previous index and is on the same node."""
        return self.node == other.node and self.index == other.index + 1

    def get_successor_number(self):
        """Return next index on node."""
        return self.node, self.index + 1

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.node, self.index) < (other.node, other.index)


class SpikeDMD(DmdPlatformInterface):

    """The DMD on the SPIKE system."""

    __slots__ = ["platform", "data", "new_frame_event", "dmd_task"]

    def __init__(self, platform):
        """initialize DMD."""
        self.platform = platform
        self.data = None
        self.new_frame_event = asyncio.Event()
        self.dmd_task = platform.machine.clock.loop.create_task(self._dmd_send())
        self.dmd_task.add_done_callback(Util.raise_exceptions)

    def stop(self):
        """Stop dmd task."""
        if self.dmd_task:
            self.dmd_task.cancel()
            try:
                self.platform.machine.clock.loop.run_until_complete(self.dmd_task)
            except asyncio.CancelledError:
                pass
            self.dmd_task = None

    def update(self, data: bytes):
        """Remember the last frame data."""
        self.data = data
        self.new_frame_event.set()

    async def _dmd_send(self):
        while True:
            await self.new_frame_event.wait()
            self.new_frame_event.clear()
            await self.send_update()
            # sleep at least 5ms
            await asyncio.sleep(.005)

    async def send_update(self):
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
        await self.platform.send_cmd_raw(bytes([0x80, 0x00, 0x90]) + bytes(frame1) + bytes(frame2) +
                                         bytes(frame3) + bytes(frame4))

    def set_brightness(self, brightness: float):
        """Set brightness of the DMD."""
        # we do not yet know how that works in SPIKE


class SpikeDriver(DriverPlatformInterface):

    """A driver on a Stern Spike node board."""

    __slots__ = ["platform", "node", "index", "_enable_task"]

    def __init__(self, config, number, platform):
        """initialize driver on Stern Spike."""
        super().__init__(config, number)
        self.platform = platform
        self.node, self.index = number.split("-")
        self.node = int(self.node)
        self.index = int(self.index)
        self._enable_task = None

    def trigger(self, power1, duration1, power2, duration2):
        """Pulse the driver."""
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

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable coil."""
        if self._enable_task:
            return

        # initial pulse
        power1 = int(pulse_settings.power * 255)
        duration1 = int(pulse_settings.duration * self.platform.ticks_per_sec[self.node] / 1000)

        if duration1 > 0x1FF:
            raise AssertionError("Initial pulse too long.")

        # then enable hold
        power2 = int(hold_settings.power * 255)
        duration2 = 0x1FF

        self.trigger(power1, duration1, power2, duration2)

        self._enable_task = self.platform.machine.clock.loop.create_task(self._enable(power2))
        self._enable_task.add_done_callback(Util.raise_exceptions)

    async def _enable(self, power):
        while True:
            await asyncio.sleep(.25)
            self.trigger(power, 0x1FF, power, 0x1FF)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse coil for a certain time."""
        power1 = power2 = int(pulse_settings.power * 255)
        duration1 = int(pulse_settings.duration * self.platform.ticks_per_sec[self.node] / 1000)
        duration2 = duration1 - 0x1FF if duration1 > 0x1FF else 0
        if duration2 > 0x1FF:
            raise AssertionError("Pulse ms too long.")

        self.trigger(power1, duration1, power2, duration2)

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError

    def disable(self):
        """Disable coil."""
        # cancel enable task
        if self._enable_task:
            self._enable_task.cancel()
            self._enable_task = None

        # disable coil
        self.trigger(0, 0, 0, 0)

    def get_board_name(self):
        """Return name for service mode."""
        return SPIKE_NODE_FORMAT.format(self.node)


class SpikeStepper(StepperPlatformInterface):

    """A stepper in Spike."""

    __slots__ = ["number", "node", "stepper_id", "config", "platform", "_position", "light_index"]

    def __init__(self, number, config, platform):
        """initialize stepper."""
        self.number = number
        node, index = number.split("-", 2)
        self.node = int(node)
        self.stepper_id = int(index)
        self.config = config
        self.platform = platform    # type: SpikePlatform
        self._position = 0
        light_node, light_index = self.config['light_number'].split("-", 2)
        if light_node != node:
            self.platform.raise_config_error("Light and Stepper have to be on the same node."
                                             " Light: {} Stepper: {}".format(number, self.config['light_number']), 1)
        self.light_index = int(light_index)
        self._configure()

    def home(self, direction):
        """Unsupported."""
        raise AssertionError("Use a switch.")

    def set_home_position(self):
        """Set position to home."""
        self._mark_as_home()

    def _configure(self):
        """Configure stepper in spike."""
        unknown1 = 200
        unknown2 = 0
        unknown3 = 0xff
        self.platform.send_cmd_async(self.node, SpikeNodebus.StepperConfig, [
            self.stepper_id,
            unknown1,                   # unclear what it does
            unknown2 & 0xff,            # unclear what it does
            (unknown2 >> 8) & 0xff,
            self.light_index + 0x40,
            unknown3                    # unclear what it does
        ])

    def _mark_as_home(self):
        """Tell the node that the stepper is home."""
        self.platform.send_cmd_async(self.node, SpikeNodebus.StepperHome, [
            self.stepper_id
        ])

    async def _get_stepper_info(self):
        """Get info about the stepper."""
        '''
        position (u16), unknown (u16), flags (u8)
        flags:
            0 - unknown
            1 - is_active
            2 - unknown
            3 - unknown
            4 - unknown
            5 - unknown
            6 - unknown
            7 - unknown

        Typical response: 17 00 18 00 01 d0 00
        '''
        result = await self.platform.send_cmd_and_wait_for_response(
            self.node, SpikeNodebus.StepperInfo + self.stepper_id, [], 7)
        if result is None:
            self.platform.warning_log("Failed to read stepper %s position", self.number)
            return None
        return {
            "position": result[0] + (result[1] << 8),
            "is_active": bool((result[4] >> 1) & 1)
        }

    def _move_to_absolute_position(self, position, speed):
        """Move the stepper to a certain position."""
        self.platform.send_cmd_async(self.node, SpikeNodebus.StepperSet, [
            self.stepper_id,
            position & 0xff,
            (position >> 8) & 0xff,
            speed
        ])

    async def wait_for_move_completed(self):
        """Wait until move completed."""
        while not await self.is_move_complete():
            await asyncio.sleep(1 / self.config['poll_ms'])

    async def is_move_complete(self) -> bool:
        """Return true if move is complete."""
        info = await self._get_stepper_info()
        if info is None:
            # read did fail
            return False
        return info['position'] == self._position

    def move_rel_pos(self, position):
        """Move relative to current position."""
        self._position += int(position)
        self._move_to_absolute_position(self._position, self.config['speed'])

    def move_vel_mode(self, velocity):
        """Move stepper in a direction."""
        # this is not really supported and we could do better here
        # also we do not know how to move to the other direciton
        if velocity < 0:
            raise AssertionError("We do not know how to do this in Spike. Let us know if you need it.")
        self._move_to_absolute_position(200, self.config['homing_speed'])

    def stop(self):
        """Stop the stepper."""
        # reconfiguring seems to be used to stop the stepper
        self._configure()


# pylint: disable-msg=too-many-instance-attributes
class SpikePlatform(SwitchPlatform, LightsPlatform, DriverPlatform, DmdPlatform, StepperPlatform):

    """Stern Spike Platform."""

    __slots__ = ["_writer", "_reader", "_inputs", "config", "_poll_task", "_sender_task", "_send_key_task", "dmd",
                 "_nodes", "_bus_read", "_bus_write", "_cmd_queue", "ticks_per_sec", "_light_system",
                 "node_firmware_version", "_query_nodes_task"]

    def __init__(self, machine):
        """initialize spike hardware platform."""
        super().__init__(machine)
        self._writer = None
        self._reader = None
        self._inputs = {}
        self._poll_task = None
        self._sender_task = None
        self._send_key_task = None
        self._query_nodes_task = None
        self.dmd = None
        self.features['has_lights'] = True

        self._nodes = None
        self._bus_read = asyncio.Lock()
        self._bus_write = asyncio.Lock()
        self._cmd_queue = asyncio.Queue()

        self._light_system = None

        self.ticks_per_sec = {
            0: 1
        }
        self.node_firmware_version = {
            0: 0x000000
        }

        self.config = self.machine.config_validator.validate_config("spike", self.machine.config['spike'])
        self._configure_device_logging_and_debug("Spike", self.config)

    @classmethod
    def get_switch_config_section(cls):
        """Return switch config section."""
        return "spike_switch_overwrites"

    async def _send_multiple_light_update(self, sequential_brightness_list):
        common_fade_ms = sequential_brightness_list[0][2]
        if common_fade_ms < 0:
            common_fade_ms = 0
        fade_time = int(common_fade_ms * self.ticks_per_sec[sequential_brightness_list[0][0].node] / 1000)

        if self.node_firmware_version[sequential_brightness_list[0][0].node] >= 0x4100:
            # firmware 0.65.0+ changed the data format for SpikeNodebus.SetLed we use another command until we
            # understand what happened there
            # advantage of SpikeNodebus.SetRGBMulti: it supports LED index > 0x20
            data = bytearray([sequential_brightness_list[0][0].index & 0xFF,
                              (sequential_brightness_list[0][0].index & 0xFF00) >> 8,
                              fade_time])
            for _, brightness, _ in sequential_brightness_list:
                data.append(int(255 * brightness))
            self.send_cmd_async(sequential_brightness_list[0][0].node,
                                SpikeNodebus.SetRGBMulti, data)
        else:
            data = bytearray([fade_time])
            for _, brightness, _ in sequential_brightness_list:
                data.append(int(255 * brightness))
            self.send_cmd_async(sequential_brightness_list[0][0].node,
                                SpikeNodebus.SetLed + sequential_brightness_list[0][0].index, data)

    # pylint: disable-msg=too-many-arguments
    def _write_rule(self, node, enable_switch_index, disable_switch_index, coil_index, pulse_settings: PulseSettings,
                    hold_settings: Optional[HoldSettings], param1, param2, param3, hold_param1=0):
        """Write a hardware rule to Stern Spike.

        [14] is used in CoilReflex. Might be debounce? (NODEBUS_CoilConfig param_3[1] (ushort))
            Slings = 0xf5
            Pops = 0x14
            Flippers = 0

        We do not yet understand param1, param2 and param3:
        param1 == 2 -> second switch (eos switch)
        param2 == 1 -> ??
        param2 == 6 -> ??
        param3 == 5 -> allow enable
        """
        pulse_value = int(pulse_settings.duration * self.ticks_per_sec[node] / 1000)

        if self.node_firmware_version[node] >= 0x4100:
            # firmware 0.65.0+ length: 0x2d = 45
            # flippers (deadpool 0.65.0):
            # \x88\x2d\x41\x05\xff\x33\x00\x1e\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x59\x00
            # \x00\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x00\xd9\x00", 48
            # \x88\x2d\x41\x00\xff\x33\x00\x1e\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x58\x00
            # \x00\x5f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x00\xd0\x00", 48
            # pops:
            # \x89\x2d\x41\x02\xff\x28\x00\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x5c\x00
            # \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x70\x00", 48
            # \x89\x2d\x41\x03\xff\x28\x00\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x5d\x00
            # \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x6e\x00", 48
            # \x89\x2d\x41\x04\xff\x28\x00\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x5e\x00
            # \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x6c\x00", 48
            # slings:
            # \x88\x2d\x41\x03\xff\x17\x00\x00\x00\x00\x00\x00\x00\x00\xf5\x00\x00\x00\x00\x00\x00\x00\x00\x00\x5e\x00
            # \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x9e\x00", 48
            # \x88\x2d\x41\x02\xff\x17\x00\x00\x00\x00\x00\x00\x00\x00\xf5\x00\x00\x00\x00\x00\x00\x00\x00\x00\x5d\x00
            # \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa0\x00", 48
            self.send_cmd_async(node, SpikeNodebus.CoilSetReflex, bytearray(
                [coil_index,                                                # coil [3]
                 int(pulse_settings.power * 255),                           # pulse power (coil1)[4]
                 pulse_value & 0xFF,                                        # pulse time lower (coil1) [5]
                 (pulse_value & 0xFF00) >> 8,                               # pulse time upper (coil2) [6]
                 int(hold_settings.power * 255) if hold_settings else 0,    # hold power (coil1) [7]
                 hold_param1,                                               # some time lower (probably pulse coil2) [8]
                 0x00,                                                      # some time upper (probably pulse coil2) [9]
                 0x00,                                                      # some time lower (unknown) [10]
                 0x00,                                                      # some time upper (unknown) [11]
                 0,                                                         # a unknown time lower (1) [12]
                 0,                                                         # a unknown time upper (1) [13]
                 0,                                                         # a unknown time lower (2) [14]
                 0,                                                         # a unknown time upper (2) [15]
                 0,                                                         # a unknown time lower (3) [16]
                 0,                                                         # a unknown time upper (3) [17]
                 0,                                                         # a unknown time lower (4) [18]
                 0,                                                         # a unknown time upper (4) [19]
                 0,                                                         # a unknown time lower (5) [20]
                 0,                                                         # a unknown time upper (5) [21]
                 0,
                 0,
                 0x40 ^ enable_switch_index,                                # enable switch [22]
                 0,                                                         # another switch? [23]
                 0,                                                         # another switch? [24]
                 0x40 ^ disable_switch_index if disable_switch_index is not None else 0,  # disable switch [25]
                 0,                                                         # another switch? [26]
                 0,                                                         # another switch? [27]
                 0,                                                         # another switch? [28]
                 0,                                                         # another switch? [29]
                 0,                                                         # param5 [30]
                 0,                                                         # param5 [31]
                 0,                                                         # param5 [32]
                 0,                                                         # param5 [33]
                 0,
                 0,
                 0,
                 0,
                 0,
                 0,
                 0,
                 param1,                                                    # some time (param6) [34]
                 param2,                                                    # param7 [35]
                 param3                                                     # param8 [36]
                 ]))

        elif self.node_firmware_version[node] >= 0x2800:
            # firmware 0.40.0+ length: 0x24 = 36
            self.send_cmd_async(node, SpikeNodebus.CoilSetReflex, bytearray(
                [coil_index,                                                # coil [3]
                 int(pulse_settings.power * 255),                           # pulse power (coil1)[4]
                 pulse_value & 0xFF,                                        # pulse time lower (coil1) [5]
                 (pulse_value & 0xFF00) >> 8,                               # pulse time upper (coil2) [6]
                 int(hold_settings.power * 255) if hold_settings else 0,    # hold power (coil1) [7]
                 hold_param1,                                               # some time lower (probably pulse coil2) [8]
                 0x00,                                                      # some time upper (probably pulse coil2) [9]
                 0x00,                                                      # some time lower (unknown) [10]
                 0x00,                                                      # some time upper (unknown) [11]
                 0,                                                         # a unknown time lower (1) [12]
                 0,                                                         # a unknown time upper (1) [13]
                 0,                                                         # a unknown time lower (2) [14]
                 0,                                                         # a unknown time upper (2) [15]
                 0,                                                         # a unknown time lower (3) [16]
                 0,                                                         # a unknown time upper (3) [17]
                 0,                                                         # a unknown time lower (4) [18]
                 0,                                                         # a unknown time upper (4) [19]
                 0,                                                         # a unknown time lower (5) [20]
                 0,                                                         # a unknown time upper (5) [21]
                 0x40 ^ enable_switch_index,                                # enable switch [22]
                 0,                                                         # another switch? [23]
                 0,                                                         # another switch? [24]
                 0x40 ^ disable_switch_index if disable_switch_index is not None else 0,  # disable switch [25]
                 0,                                                         # another switch? [26]
                 0,                                                         # another switch? [27]
                 0,                                                         # another switch? [28]
                 0,                                                         # another switch? [29]
                 0,                                                         # param5 [30]
                 0,                                                         # param5 [31]
                 0,                                                         # param5 [32]
                 0,                                                         # param5 [33]
                 param1,                                                    # some time (param6) [34]
                 param2,                                                    # param7 [35]
                 param3                                                     # param8 [36]
                 ]))
        else:
            # length: 0x19
            self.send_cmd_async(node, SpikeNodebus.CoilSetReflex, bytearray(
                [coil_index,                                                # coil [3]
                 int(pulse_settings.power * 255),                           # pulse power [4]
                 pulse_value & 0xFF,                                        # pulse time lower [5]
                 (pulse_value & 0xFF00) >> 8,                               # pulse time upper [6]
                 int(hold_settings.power * 255) if hold_settings else 0,    # hold power [7]
                 0x00,                                                      # some time lower (probably hold) [8]
                 0x00,                                                      # some time upper (probably hold) [9]
                 0x00,                                                      # some time lower (unknown) [10]
                 0x00,                                                      # some time upper (unknown) [11]
                 0,                                                         # a unknown time lower (1) [12]
                 0,                                                         # a unknown time upper (1) [13]
                 0,                                                         # a unknown time lower (2) [14]
                 0,                                                         # a unknown time upper (2) [15]
                 0,                                                         # a unknown time lower (3) [16]
                 0,                                                         # a unknown time upper (3) [17]
                 0,                                                         # a unknown time lower (4) [18]
                 0,                                                         # a unknown time upper (4) [19]
                 0x40 ^ enable_switch_index,                                # enable switch [20]
                 0x40 ^ disable_switch_index if disable_switch_index is not None else 0,    # disable switch [21]
                 0,                                                         # another switch? [22]
                 param1,                                                    # param5 [23]
                 param2,                                                    # some time (param6) [24]
                 param3                                                     # param7 [25]
                 ]))

    @staticmethod
    def _check_coil_switch_combination(switch, coil):
        if switch.hw_switch.node != coil.hw_driver.node:
            raise AssertionError("Coil {} and Switch {} need to be on the same node to write a rule".format(
                coil, switch
            ))

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        This is mostly used for popbumpers. Example from WWE:
        Type: 8 Cmd: 65 Node: 9 Msg: 0x00 0xa6 0x28 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x14 0x00 0x00 0x00 0x38
        0x00 0x40 0x00 0x00 0x00 0x00 0x00 Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        enable_switch.hw_switch.configure_debounce_and_recycle(enable_switch.debounce, enable_switch.invert,
                                                               coil.recycle)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index ^ (enable_switch.invert * 0x40),
                         None, coil.hw_driver.index,
                         coil.pulse_settings, None, 0, 0, 0)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release rule on driver.

        Used for single coil flippers. Examples from WWE:
        Dual-wound flipper hold coil:
        Type: 8 Cmd: 65 Node: 8 Msg: 0x02 0xff 0x46 0x01 0xff 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x3a
        0x00 0x42 0x40 0x00 0x00 0x01 0x00  Len: 25

        Ring Slings (different flags):
        Type: 8 Cmd: 65 Node: 10 Msg: 0x00 0xff 0x19 0x00 0x14 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x80
        0x00 0x4a 0x40 0x00 0x00 0x06 0x05  Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        enable_switch.hw_switch.configure_debounce_and_recycle(enable_switch.debounce, enable_switch.invert,
                                                               coil.recycle)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index ^ (enable_switch.invert * 0x40),
                         None, coil.hw_driver.index,
                         coil.pulse_settings, coil.hold_settings, 0, 6, 5)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and release rule to driver.

        Used for high-power coil on dual-wound flippers. Example from WWE:
        Type: 8 Cmd: 65 Node: 8 Msg: 0x00 0xff 0x33 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x42 0x40 0x00 0x02 0x06 0x00  Len: 25
        """
        self._check_coil_switch_combination(enable_switch, coil)
        self._check_coil_switch_combination(eos_switch, coil)

        if self.node_firmware_version[coil.hw_driver.node] >= 0x2800:
            flag1 = 5
            hold_param1 = 0x28
        else:
            flag1 = 2
            hold_param1 = 0

        enable_switch.hw_switch.configure_debounce_and_recycle(enable_switch.debounce, enable_switch.invert,
                                                               coil.recycle)
        eos_switch.hw_switch.configure_debounce_and_recycle(eos_switch.debounce, eos_switch.invert,
                                                            coil.recycle)

        # this might have to be the same flags as set_pulse_on_hit_and_enable_and_release_and_disable_rule
        # it might also just depend on Spike System 1 vs 2
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index ^ (enable_switch.invert * 0x40),
                         eos_switch.hw_switch.index ^ (eos_switch.invert * 0x40),
                         coil.hw_driver.index, coil.pulse_settings, coil.hold_settings, flag1, 6, 0,
                         hold_param1=hold_param1)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and release rule to driver.

        Used for high-power coil on single-wound flippers. Example from GoT:
        Node: 8 Command CoilSetReflex (0x41) Params: 0x00 0xff 0x33 0x00 0x1e 0x28 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x00 0x00 0x00 0x00 0x00 0x42 0x00 0x00 0x40 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x05 0x06 0x00 Len: 36
        """
        self._check_coil_switch_combination(enable_switch, coil)
        self._check_coil_switch_combination(eos_switch, coil)

        if self.node_firmware_version[coil.hw_driver.node] >= 0x2800:
            flag1 = 5
            hold_param1 = 0x28
        else:
            flag1 = 2
            hold_param1 = 0
        enable_switch.hw_switch.configure_debounce_and_recycle(enable_switch.debounce, enable_switch.invert,
                                                               coil.recycle)
        eos_switch.hw_switch.configure_debounce_and_recycle(eos_switch.debounce, eos_switch.invert,
                                                            coil.recycle)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index ^ (enable_switch.invert * 0x40),
                         eos_switch.hw_switch.index ^ (eos_switch.invert * 0x40),
                         coil.hw_driver.index, coil.pulse_settings, coil.hold_settings, flag1, 6, 0,
                         hold_param1=hold_param1)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver.

        I believe that param2 == 1 means that it will cancel the pulse when the switch is released.

        Used for high-power coils on dual-wound flippers. Example from WWE:
        Type: 8 Cmd: 65 Node: 8 Msg: 0x03 0xff 0x46 0x01 0xff 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        0x00 0x43 0x40 0x00 0x00 0x01 0x00  Len: 25

        """
        self._check_coil_switch_combination(enable_switch, coil)
        enable_switch.hw_switch.configure_debounce_and_recycle(enable_switch.debounce, enable_switch.invert,
                                                               coil.recycle)
        self._write_rule(coil.hw_driver.node, enable_switch.hw_switch.index ^ (enable_switch.invert * 0x40),
                         None, coil.hw_driver.index,
                         coil.pulse_settings, None, 0, 1, 0)

    def clear_hw_rule(self, switch, coil):
        """Disable hardware rule for this coil."""
        del switch
        if self.node_firmware_version[coil.hw_driver.node] >= 0x2800:
            self.send_cmd_async(coil.hw_driver.node, SpikeNodebus.CoilSetReflex, bytearray(
                [coil.hw_driver.index] + [0x00] * 33))
        else:
            self.send_cmd_async(coil.hw_driver.node, SpikeNodebus.CoilSetReflex, bytearray(
                [coil.hw_driver.index, 0, 0, 0, 0, 0x00, 0x00, 0x00, 0x00,
                 0, 0, 0, 0, 0, 0, 0, 0,
                 0, 0, 0,
                 0, 0, 0]))

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure a driver on Stern Spike."""
        del platform_settings

        try:
            node, _ = number.split("-")
        except IndexError:
            return self.raise_config_error("Coil number has to have the syntax node-index but is:"
                                           " {} for driver {}".format(number, config.name),
                                           4)

        if int(node) not in self._nodes:
            self.raise_config_error("Node {} not known for coil {}".format(node, number), 5)

        return SpikeDriver(config, number, self)

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Return a single light."""
        return [
            {
                "number": number,
            }
        ]

    def configure_light(self, number, subtype, config, platform_settings) -> Union[SpikeLight, SpikeBacklight]:
        """Configure a light on Stern Spike."""
        del platform_settings, subtype
        if number == "0-0":
            return SpikeBacklight(number, self, self.machine.clock.loop, 3)

        try:
            node, index = number.split("-")
        except IndexError:
            return self.raise_config_error("Light number has to have the syntax node-index but is:"
                                           " {} for light {}".format(number, config.name),
                                           7)

        if int(node) in self.config['node_config'] and \
                self.config['node_config'][int(node)]['num_leds'] is not None and \
                int(index) > self.config['node_config'][int(node)]['num_leds']:
            return self.raise_config_error("Light {} is larger than the maximum configured led {} for "
                                           "node {}".format(number,
                                                            self.config['node_config'][int(node)]['num_leds'],
                                                            node), 8)

        # TODO: validate that light number is not used in a stepper and a light
        return SpikeLight(number, self, self._light_system)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure switch on Stern Spike."""
        try:
            node, index = number.split("-")
        except IndexError:
            return self.raise_config_error("Switch number has to have the syntax node-index but is:"
                                           " {} for switch {}".format(number, config.name),
                                           2)

        if int(node) not in self._nodes:
            self.raise_config_error("Node {} not known for switch {}".format(node, number), 3)

        if int(node) in self.config['node_config'] and \
                self.config['node_config'][int(node)]['num_inputs'] is not None and \
                int(index) > self.config['node_config'][int(node)]['num_inputs']:
            return self.raise_config_error("Switch {} is larger than the maximum configured input {} for "
                                           "node {}".format(number,
                                                            self.config['node_config'][int(node)]['num_inputs'],
                                                            node), 6)

        switch = SpikeSwitch(config, number, self, platform_config)
        switch.configure_debounce_and_recycle(config.debounce, config.invert, False)
        return switch

    async def get_hw_switch_states(self):
        """Return current switch states."""
        hw_states = dict()
        for node in self._nodes:
            curr_bit = 1
            for index in range(0, 64):
                hw_states[str(node) + '-' + str(index)] = (curr_bit & self._inputs[node]) == 0
                curr_bit <<= 1
        return hw_states

    async def initialize(self):
        """initialize platform."""
        port = self.config['port']
        baud = self.config['baud']
        flow_control = self.config['flow_control']
        self.debug = self.config['debug']
        self._nodes = self.config['nodes']

        if 0 not in self._nodes:
            raise AssertionError("Please include CPU node 0 in nodes for Spike.")

        await self._connect_to_hardware(port, baud, flow_control=flow_control)

        self._poll_task = asyncio.create_task(self._poll())
        self._poll_task.add_done_callback(Util.raise_exceptions)

        self._sender_task = asyncio.create_task(self._sender())
        self._sender_task.add_done_callback(Util.raise_exceptions)

        if self.config['use_send_key']:
            self._send_key_task = asyncio.create_task(self._send_key())
            self._send_key_task.add_done_callback(Util.raise_exceptions)

        if self.config['periodically_query_nodes']:
            self._query_nodes_task = asyncio.create_task(self._query_status_and_coil_current())
            self._query_nodes_task.add_done_callback(Util.raise_exceptions)

        self._light_system = PlatformBatchLightSystem(self.machine.clock, self._send_multiple_light_update,
                                                      self.machine.config['mpf']['default_light_hw_update_hz'],
                                                      self.config['max_led_batch_size'])
        self._light_system.start()

    async def _connect_to_hardware(self, port, baud, *, flow_control=False, xonxoff=False):
        self.info_log("Connecting to %s at %sbps", port, baud)

        connector = self.machine.clock.open_serial_connection(
            url=port, baudrate=baud, rtscts=flow_control, xonxoff=xonxoff)
        self._reader, self._writer = await connector
        self._writer.transport.set_write_buffer_limits(2048, 1024)

        await self._initialize()

    async def _update_switches(self, node):
        if node not in self._nodes:     # pragma: no cover
            self.warning_log("Cannot read node %s because it is not configured.", node)
            return False

        new_inputs_str = await self._read_inputs(node)
        if not new_inputs_str:      # pragma: no cover
            self.info_log("Node: %s did not return any inputs.", node)
            return True

        new_inputs = self._input_to_int(new_inputs_str)

        if self.debug:
            self.debug_log("Inputs node: %s State: %s Old: %s New: %s",
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
            self.debug_log("Got input activity but inputs did not change.")

        self._inputs[node] = new_inputs

        return True

    async def _sender(self):
        while True:
            cmd, wait_ms = await self._cmd_queue.get()
            await self._send_cmd_without_response(cmd, wait_ms)

    async def _send_key(self):
        while True:
            for node in self._nodes:
                # do not send watchdog to cpu since it is a virtual node
                if node == 0:
                    continue

                # generate super secret "key"
                key = bytearray()
                for _ in range(16):
                    key.append(random.randint(0, 255))

                # send SendKey message
                await self.send_cmd_sync(node, SpikeNodebus.SendKey, key)

                # wait one second
                await asyncio.sleep(1.0)

    async def _query_status_and_coil_current(self):
        while True:
            for node in self._nodes:
                # do not query virtual node
                if node == 0:
                    continue

                self.debug_log("GetStatus and GetCoilCurrent on node %s", node)
                await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)
                await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetCoilCurrent, bytearray([0]), 12)

                # wait before querying the next board
                await asyncio.sleep(.5)

    async def _poll(self):
        while True:
            async with self._bus_read:
                async with self._bus_write:
                    await self._send_raw(bytearray([0]))

                try:
                    result = await asyncio.wait_for(self._read_raw(1), 2)
                except asyncio.TimeoutError:    # pragma: no cover
                    self.warning_log("Spike watchdog expired.")
                    # clear buffer
                    # pylint: disable-msg=protected-access
                    self._reader._buffer = bytearray()
                    continue

            if not result:
                self.warning_log("Empty poll result. Spike desynced.")
                # give it a break of 50ms
                await asyncio.sleep(.05)
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
                result = await self._update_switches(ready_node)
                if not result:
                    self.warning_log("Spike desynced during input.")
                    await asyncio.sleep(.05)
                    # clear buffer
                    # pylint: disable-msg=protected-access
                    self._reader._buffer = bytearray()
            elif ready_node > 0:    # pragma: no cover
                # invalid node ids
                self.warning_log("Spike desynced (invalid node %s).", ready_node)
                # give it a break of 50ms
                await asyncio.sleep(.05)
                # clear buffer
                # pylint: disable-msg=protected-access
                self._reader._buffer = bytearray()
            else:
                # sleep only if spike is idle
                await asyncio.sleep(1 / self.config['poll_hz'])

    def stop(self):
        """Stop hardware and close connections."""
        if self.dmd:
            self.dmd.stop()

        if self._light_system:
            self._light_system.stop()
        if self._poll_task:
            self._poll_task.cancel()
            try:
                self.machine.clock.loop.run_until_complete(self._poll_task)
            except asyncio.CancelledError:
                pass

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

        if self._query_nodes_task:
            self._query_nodes_task.cancel()
            try:
                self.machine.clock.loop.run_until_complete(self._query_nodes_task)
            except asyncio.CancelledError:
                pass

        if self._writer:
            # shutdown the bridge
            self._writer.write(b'\xf5')
            # send ctrl+c to stop the mpf-spike-bridge
            self._writer.write(b'\x03reset\n')
            self._writer.close()

    async def _send_raw(self, data):
        if self.debug:
            self.debug_log("Sending: %s", "".join("%02x " % b for b in data))
        for start in range(0, len(data), 256):
            block = data[start:start + 256]
            self._writer.write(bytes(block))
        await self._writer.drain()

    async def _read_raw(self, msg_len: int) -> bytearray:
        if not msg_len:
            raise AssertionError("Cannot read 0 length")

        if self.debug:
            self.debug_log("Reading %s bytes", msg_len)

        data = await self._reader.readexactly(msg_len)

        if self.debug:
            self.debug_log("Data: %s", "".join("%02x " % b for b in data))

        return data

    @staticmethod
    def _checksum(cmd_str):
        checksum = 0
        for i in cmd_str:
            checksum += i
        return (256 - (checksum % 256)) % 256

    async def send_cmd_and_wait_for_response(self, node, cmd, data, response_len) -> Optional[bytearray]:
        """Send cmd and wait for response."""
        assert response_len > 0
        if node > 15:
            raise AssertionError("Node must be 0-15.")
        cmd_str = bytearray()
        cmd_str.append((8 << 4) + node)
        cmd_str.append(len(data) + 2)
        cmd_str.append(cmd)
        cmd_str.extend(data)
        cmd_str.append(self._checksum(cmd_str))
        cmd_str.append(response_len)
        async with self._bus_read:
            async with self._bus_write:
                await self._send_raw(cmd_str)
            try:
                response = await asyncio.wait_for(self._read_raw(response_len), 2)    # type: bytearray
            except asyncio.TimeoutError:    # pragma: no cover
                self.warning_log("Failed to read %s bytes from Spike", response_len)
                return None

            if response[-1] != 0:
                self.info_log("Bridge Status: %s != 0", response[-1])
            if self.config['verify_checksums_on_readback'] and self._checksum(response[0:-1]) != 0:   # pragma: no cover
                self.warning_log("Checksum mismatch for response: %s", "".join("%02x " % b for b in response))
                # we resync by flushing the input
                self._writer.transport.serial.reset_input_buffer()
                # pylint: disable-msg=protected-access
                self._reader._buffer = bytearray()
                return None

            return response

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

    def _get_wait_ms_for_cmd(self, cmd):
        if (cmd & 0xF0) == 0x80:
            # special case for LED updates
            return self.config['wait_times'][0x80] if 0x80 in self.config['wait_times'] else 0

        return self.config['wait_times'][cmd] if cmd in self.config['wait_times'] else 0

    async def send_cmd_sync(self, node, cmd, data):
        """Send cmd which does not require a response."""
        cmd_str = self._create_cmd_str(node, cmd, data)
        wait_ms = self._get_wait_ms_for_cmd(cmd)
        await self._send_cmd_without_response(cmd_str, wait_ms)

    async def _send_cmd_without_response(self, cmd_str, wait_ms):
        async with self._bus_write:
            await self._send_raw(cmd_str)
            if wait_ms:
                await self._send_raw(bytearray([1, wait_ms]))

    async def send_cmd_raw(self, data, wait_ms=0):
        """Send raw command."""
        async with self._bus_write:
            await self._send_raw(data)
            if wait_ms:
                await self._send_raw(bytearray([1, wait_ms]))

    def send_cmd_async(self, node, cmd, data):
        """Send cmd which does not require a response."""
        cmd_str = self._create_cmd_str(node, cmd, data)
        wait_ms = self._get_wait_ms_for_cmd(cmd)
        # queue command
        self._cmd_queue.put_nowait((cmd_str, wait_ms))

    def send_cmd_raw_async(self, data, wait_ms=0):
        """Send raw cmd which does not require a response."""
        # queue command
        self._cmd_queue.put_nowait((data, wait_ms))

    def _read_inputs(self, node):
        if self.node_firmware_version[node] >= 0x2800:
            # in node firmware 0.40.0 and newer the response uses 12 bytes (10 payload)
            return self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetInputState, bytearray(), 12)

        # older firmware used 10 bytes responses (8 payload)
        return self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetInputState, bytearray(), 10)

    @staticmethod
    def _input_to_int(state):
        if state is False or state is None or len(state) < 8:
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

    async def configure_stepper(self, number: str, config: dict) -> "StepperPlatformInterface":
        """Configure a stepper in Spike."""
        # TODO: validate that light number is not used in a stepper and a light
        return SpikeStepper(number, config, self)

    @classmethod
    def get_stepper_config_section(cls):
        """Return config validator name."""
        return "spike_stepper_settings"

    async def _get_node_status(self, node):
        """Return node status report."""
        node_status = await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetStatus, bytearray(), 10)
        if node_status:
            self.debug_log("Node: %s Status: %s", node, "".join(HEX_FORMAT % b for b in node_status))
        else:
            self.warning_log("Did not get status for node %s", node)
        return node_status

    async def _init_bridge(self):
        # send ctrl+c to stop whatever is running
        self.debug_log("Resetting console")
        self._writer.write(b'\x03reset\n')
        # wait for the serial
        await asyncio.sleep(.1)
        # flush input
        self._writer.transport.serial.reset_input_buffer()
        # pylint: disable-msg=protected-access
        self._reader._buffer = bytearray()
        # start mpf-spike-bridge
        self.debug_log("Starting MPF bridge")
        if self.config['bridge_debug']:
            log_file = self.config['bridge_debug_log']
            binary = "RUST_BACKTRACE=full {}".format(self.config['bridge_path'])
        else:
            log_file = "/dev/null"
            binary = self.config['bridge_path']

        if self.config['spike_version'] == "1":
            spike_version = "SPIKE1"
        else:
            spike_version = "SPIKE2"
        self._writer.write("{} {} {} 2>{}\r\n".format(binary, self.config['runtime_baud'], spike_version,
                                                      log_file).encode())

        welcome_str = b'MPF Spike Bridge!'
        await asyncio.sleep(.1)
        # read until first capital M
        while True:
            byte = await self._reader.readexactly(1)
            if ord(byte) == welcome_str[0]:
                break

        data = await self._reader.read(100)
        if data[:len(welcome_str) - 1] != welcome_str[1:]:
            raise AssertionError("Expected '{}' got '{}'".format(welcome_str[1:], data[:len(welcome_str) - 1]))
        self.debug_log("Bridge started")

        if self.config['runtime_baud']:
            # increase baud rate
            self.debug_log("Increasing baudrate to %s", self.config['runtime_baud'])
            self._writer.transport.serial.baudrate = self.config['runtime_baud']

        await asyncio.sleep(.1)
        self._reader._buffer = bytearray()

    # pylint: disable-msg=too-many-statements
    # pylint: disable-msg=too-many-branches
    async def _initialize(self) -> None:    # noqa
        await self._init_bridge()

        self.debug_log("Resetting node bus and configuring traffic.")
        await self.send_cmd_sync(0, SpikeNodebus.Reset, bytearray())
        # wait 3s (same as spike)
        for _ in range(12):
            await self._send_raw(bytearray([1, 250]))

        await self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([34]))  # block traffic (false)
        await self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([17]))  # set traffic

        initialized_nodes = {0}

        while True:
            # poll to iterate nodes
            await self.send_cmd_raw([0])
            node_str = await self._read_raw(1)
            if node_str is None:
                self.warning_log("Initial poll timeouted")
                await asyncio.sleep(.5)
                continue

            node = node_str[0]
            if node == 0:
                # all nodes initialized
                break

            if node == 0xF0:
                # local switches. just read them to make them go away
                await self._read_inputs(0)
                continue

            initialized_nodes.add(node)
            self.debug_log("Poll nodes: %s", node)

            await self.send_cmd_sync(node, SpikeNodebus.SetTraffic, bytearray([16]))  # clear traffic
            await self.send_cmd_sync(node, SpikeNodebus.SetTraffic, bytearray([32]))  # block traffic (true)

            if node not in self._nodes:
                self.warning_log("Found a node %s during initial polling which is not configured", node)

        if set(self._nodes) - initialized_nodes:
            self.warning_log("Not all nodes found during init. Missing %s Found: %s",
                             set(self._nodes) - initialized_nodes, initialized_nodes)

        await self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([34]))  # block traffic (false)

        # get bridge version
        await self.send_cmd_raw([SpikeNodebus.GetBridgeVersion, 0, 3], 0)
        bridge_version = await self._read_raw(3)
        self.debug_log("Bridge version: %s", "".join(HEX_FORMAT % b for b in bridge_version))

        # get bridge status
        # spike seems to check if bridge_version is > 0.3.0 but that does not work for us as we saw
        # 1.0.5 in older spike machines (i.e. GoT) which used the the old version
        # we use 1.0.0 > version > 0.3.0 instead
        version = bridge_version[0] << 16 + bridge_version[1] << 8 + bridge_version[2]
        use_new_version = 0x010000 > version > 0x300
        if use_new_version:
            await self.send_cmd_raw([SpikeNodebus.GetBridgeStatus, 0, 4], 0)
            bridge_status = await self._read_raw(4)
        else:
            await self.send_cmd_raw([SpikeNodebus.GetBridgeStatus, 0, 1], 0)
            bridge_status = await self._read_raw(1)
        self.debug_log("Bridge status: %s", "".join(HEX_FORMAT % b for b in bridge_status))

        for node in self._nodes:
            if node == 0:
                continue
            self.debug_log("GetVersion on node %s", node)
            fw_version = await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetVersion, bytearray(), 12)
            if not fw_version:
                self.warning_log("Did not get version for node: %s. Ignoring node.", node)
                continue
            self.info_log("Node: %s Firmware: %s.%s.%s", node, fw_version[1], fw_version[2], fw_version[3])
            if fw_version[0] != node:
                self.warning_log("Node: %s Version Response looks bogus (node ID does not match): %s",
                                 node, "".join(HEX_FORMAT % b for b in fw_version))

            # we need this to calculate the right times for this node
            self.ticks_per_sec[node] = (fw_version[9] << 8) + fw_version[8]

            # remember firmware version of node
            self.node_firmware_version[node] = fw_version[1] << 16 | fw_version[2] << 8 | fw_version[3]

            self.debug_log("GetFullID on node %s", node)
            full_board_id_0 = await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetFullBoardId,
                                                                        bytearray([0]), 18)
            if not full_board_id_0:
                self.warning_log("Did not get full_board_id 0 for node: %s.", node)

            full_board_id_1 = await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetFullBoardId,
                                                                        bytearray([1]), 18)
            if not full_board_id_1:
                self.warning_log("Did not get full_board_id 1 for node: %s.", node)

            if full_board_id_0 and full_board_id_1:
                self.info_log("Node %s: Full Board ID: %s %s",
                              node, "".join(HEX_FORMAT % b for b in full_board_id_0),
                              "".join(HEX_FORMAT % b for b in full_board_id_1))

            # Set response time (redundant but send multiple times)
            # wait time based on the baud rate of the bus: (460800 * 0x98852841 * 200) >> 0x30 = 0x345
            response_time = self.config['response_time']
            await self.send_cmd_raw([SpikeNodebus.SetResponseTime, 0x02, int(response_time & 0xff),
                                     int(response_time >> 8), 0], 0)

            self.debug_log("GetChecksum on node %s", node)
            checksum = await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetChecksum,
                                                                 bytearray([0xff, 0x00]), 4)
            if checksum and checksum[0] == 0 and checksum[1] == 0 and checksum[2] == 0 and checksum[3] == 0:
                self.info_log("Checksum good for node %s", node)
            elif checksum:
                self.warning_log("Checksum %s for node %s is != 0000. This might indicate a broken firmware.",
                                 "".join(HEX_FORMAT % b for b in checksum), node)
            else:
                self.warning_log("Did not get checksum for node %s", node)

        for node in self._nodes:
            self.debug_log("Initial read inputs on node %s", node)
            initial_inputs = await self._read_inputs(node)
            self._inputs[node] = self._input_to_int(initial_inputs)

        for node in self._nodes:
            if node == 0:
                continue
            self.debug_log("GetStatus and GetCoilCurrent on node %s", node)
            await self._get_node_status(node)

            if self.node_firmware_version[node] >= 0x2800:
                self.debug_log("SetLEDMask, CoilSetMask, CoilSetOCTime, CoilSetOCBehavior, and SetNumLEDsInputs "
                               "on node %s", node)

                # set 96 leds and 60 inputs during OC detection
                await self.send_cmd_sync(node, SpikeNodebus.SetNumLEDsInputs, bytearray([0x60, 0, 0x40, 0]))

                # mask out all coils
                await self.send_cmd_sync(node, SpikeNodebus.CoilSetMask, bytearray([0xff, 0x01]))

                # mask out all leds
                await self.send_cmd_sync(node, SpikeNodebus.SetLEDMask, bytearray([0xff] * 12))

                # 5ms oc detect
                oc_time = int(5 * self.ticks_per_sec[node] / 1000)
                await self.send_cmd_sync(node, SpikeNodebus.CoilSetOCTime,
                                         bytearray([oc_time & 0xff, (oc_time >> 8) & 0xff]))

                for coil in range(0, 8):
                    await self.send_cmd_sync(node, SpikeNodebus.CoilSetMask, bytearray([0xff - (1 << coil), 0x01]))
                    # pulse coils
                    await self.send_cmd_sync(node, SpikeNodebus.CoilFireRelease,
                                             bytearray([coil, 0xff, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
                    await self._get_node_status(node)

                # enable all coils
                await self.send_cmd_sync(node, SpikeNodebus.CoilSetMask, bytearray([0, 0]))

                # enable all leds
                await self.send_cmd_sync(node, SpikeNodebus.SetLEDMask, bytearray([0] * 12))

                # 100ms oc time
                oc_time = int(self.config['oc_time'] * self.ticks_per_sec[node] / 1000)
                await self.send_cmd_sync(node, SpikeNodebus.CoilSetOCTime,
                                         bytearray([oc_time & 0xff, (oc_time >> 8) & 0xff]))
                # set whatever spike sets
                await self.send_cmd_sync(node, SpikeNodebus.CoilSetOCBehavior, bytearray([0x01]))

                # set number of LEDs and inputs based on node config
                if node in self.config['node_config'] and self.config['node_config'][node]["num_leds"] is not None and \
                        self.config['node_config'][node]["num_inputs"] is not None:
                    await self.send_cmd_sync(node, SpikeNodebus.SetNumLEDsInputs,
                                             bytearray([self.config['node_config'][node]["num_leds"], 0,
                                                        self.config['node_config'][node]["num_inputs"], 0]))

            await self.send_cmd_and_wait_for_response(node, SpikeNodebus.GetCoilCurrent, bytearray([0]), 12)

        for node, config in self.config['node_config'].items():
            if self.node_firmware_version[node] >= 0x2800 and config['coil_priorities']:
                # configure coil priorities
                priority_response = await self.send_cmd_and_wait_for_response(
                    node, SpikeNodebus.CoilSetPriority,
                    bytearray([len(config['coil_priorities'])] + config['coil_priorities'] +
                              [len(config['coil_priorities'])]), 3)

                if not priority_response:
                    self.warning_log("Failed to set coil priority on node %s", node)

        self.debug_log("Configuring traffic.")
        await self.send_cmd_sync(0, SpikeNodebus.SetTraffic, bytearray([0x11]))  # set traffic

        self.info_log("SPIKE init done.")
