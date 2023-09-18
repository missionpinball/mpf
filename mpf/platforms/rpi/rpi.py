"""Platform to control the hardware of a Raspberry Pi."""
import asyncio

from typing import Optional

from mpf.platforms.interfaces.i2c_platform_interface import I2cPlatformInterface

from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util

from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.core.platform import SwitchPlatform, DriverPlatform, ServoPlatform, SwitchSettings, \
    DriverSettings, DriverConfig, SwitchConfig, I2cPlatform, RepulseSettings

# apiogpio is not a requirement for MPF so we fail with a nice error when loading
try:
    import apigpio
except ImportError:
    apigpio = None

BOARD_NAME = "Raspberry Pi"


class RpiSwitch(SwitchPlatformInterface):

    """A switch on a RPI."""

    def get_board_name(self):
        """Return name."""
        return BOARD_NAME


class RpiDriver(DriverPlatformInterface):

    """An output on a Rasoberry Pi."""

    def __init__(self, number, config, platform):
        """initialize output."""
        super().__init__(config, number)
        self.platform = platform            # type: RaspberryPiHardwarePlatform
        self.gpio = int(self.number)
        self.delay = DelayManager(self.platform.machine)

    def get_board_name(self):
        """Return name."""
        return BOARD_NAME

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse output."""
        self.enable(pulse_settings, None)

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError

    def enable(self, pulse_settings: PulseSettings, hold_settings: Optional[HoldSettings]):
        """Enable output."""
        self.platform.send_command(self.platform.pi.write(self.gpio, 1))
        if hold_settings and hold_settings.power == 1:
            # do nothing. just keep driver enabled
            pass
        elif hold_settings and hold_settings.power > 0:
            # schedule pwm
            self.delay.add(pulse_settings.duration, self._pwm, hold_power=hold_settings.power)
        else:
            # no hold. disable after pulse
            self.delay.add(pulse_settings.duration, self.disable)

    def _pwm(self, hold_power):
        """Set up pwm."""
        self.platform.send_command(self.platform.pi.set_PWM_dutycycle(self.gpio, hold_power * 255))

    def disable(self):
        """Disable output."""
        self.platform.send_command(self.platform.pi.write(self.gpio, 0))
        # clear all delays
        self.delay.clear()


class RpiServo(ServoPlatformInterface):

    """A servo connected to a RPI."""

    def __init__(self, number, platform):
        """initialize servo."""
        self.gpio = int(number)
        self.platform = platform    # type: RaspberryPiHardwarePlatform

    def go_to_position(self, position):
        """Move servo to position."""
        # can be between 1000 and 2000us
        position_translated = 1000 + position * 1000
        self.platform.send_command(self.platform.pi.set_servo_pulsewidth(self.gpio, position_translated))

    def stop(self):
        """Disable servo."""
        self.platform.send_command(self.platform.pi.set_servo_pulsewidth(self.gpio, 0))

    def set_speed_limit(self, speed_limit):
        """Not implemented."""

    def set_acceleration_limit(self, acceleration_limit):
        """Not implemented."""


class RpiI2cDevice(I2cPlatformInterface):

    """A I2c device on a Rpi."""

    def __init__(self, number: str, loop, platform) -> None:
        """initialize i2c device on rpi."""
        super().__init__(number)
        self.loop = loop
        self.pi = platform.pi
        self.platform = platform
        self.number = number
        self.handle = None

    async def open(self):
        """Open I2c port."""
        self.handle = await self._get_i2c_handle(self.number)

    @staticmethod
    def _get_i2c_bus_address(address):
        """Split and return bus + address."""
        if isinstance(address, int):
            return 0, address
        bus, address = address.split("-")
        return int(bus), int(address)

    async def _get_i2c_handle(self, address):
        """Get or open handle for i2c device via pigpio."""
        bus_address, device_address = self._get_i2c_bus_address(address)
        handle = await self.pi.i2c_open(bus_address, device_address)
        return handle

    def i2c_write8(self, register, value):
        """Write to i2c via pigpio."""
        self.platform.send_command(self._i2c_write8_async(register, value))

    async def _i2c_write8_async(self, register, value):
        await self.pi.i2c_write_byte_data(self.handle, register, value)

    async def i2c_read8(self, register):
        """Read from i2c via pigpio."""
        return await self.pi.i2c_read_byte_data(self.handle, register)

    async def i2c_read_block(self, register, count):
        """Read block via I2C."""
        return await self.pi.i2c_read_i2c_block_data(self.handle, register, count)


class RaspberryPiHardwarePlatform(SwitchPlatform, DriverPlatform, ServoPlatform, I2cPlatform):

    """Control the hardware of a Raspberry Pi.

    Works locally and remotely via network.
    """

    def __init__(self, machine):
        """initialize Raspberry Pi platform."""
        super().__init__(machine)

        if not apigpio:
            raise AssertionError("To use the Raspberry Pi platform you need to install the apigpio extension. "
                                 "Run: pip3 install apigpio-mpf.")

        self.pi = None          # type: Optional[apigpio.Pi]
        # load config
        self.config = self.machine.config_validator.validate_config("raspberry_pi", self.machine.config['raspberry_pi'])
        self._switches = None   # type: Optional[int]

        self._cmd_queue = None  # type: Optional[asyncio.Queue]
        self._cmd_task = None   # type: Optional[asyncio.Task]
        self._configure_device_logging_and_debug("Raspberry Pi", self.config)

    async def initialize(self):
        """initialize platform."""
        # create pi object and connect
        self.pi = apigpio.Pi(self.machine.clock.loop)
        await self.pi.connect((self.config['ip'], self.config['port']))

        self._switches = await self.pi.read_bank_1()

        self._cmd_queue = asyncio.Queue()
        self._cmd_task = asyncio.create_task(self._run())
        self._cmd_task.add_done_callback(Util.raise_exceptions)

    def send_command(self, cmd):
        """Add a command to the command queue."""
        self._cmd_queue.put_nowait(cmd)

    async def _run(self):
        """Handle the command queue."""
        while True:
            # get next command
            cmd = await self._cmd_queue.get()
            # run command
            await cmd

            self._cmd_queue.task_done()

    def stop(self):
        """Stop platform."""
        if self._cmd_task:
            self.machine.clock.loop.run_until_complete(self._cmd_queue.join())
            self._cmd_task.cancel()
            self._cmd_task = None

        if self.pi:
            self.machine.clock.loop.run_until_complete(self.pi.stop())
            self.pi = None

    async def configure_servo(self, number: str, config: dict) -> ServoPlatformInterface:
        """Configure a servo."""
        del config
        return RpiServo(number, self)

    async def get_hw_switch_states(self):
        """Return current switch states."""
        hw_states = dict()
        curr_bit = 1
        for index in range(32):
            hw_states[str(index)] = not bool(curr_bit & self._switches)
            curr_bit <<= 1
        return hw_states

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure a switch with pull up."""
        # set input
        self.send_command(self.pi.set_mode(int(number), apigpio.INPUT))
        # configure pull up
        self.send_command(self.pi.set_pull_up_down(int(number), apigpio.PUD_UP))

        if config.debounce:
            # configure debounce to 2ms
            self.send_command(self.pi.set_glitch_filter(int(number), 2000))
        else:
            # configure debounce to 100us
            self.send_command(self.pi.set_glitch_filter(int(number), 100))

        # add callback
        self.send_command(self.pi.add_callback(int(number), apigpio.EITHER_EDGE, self._switch_changed))

        return RpiSwitch(config, number, self)

    def _switch_changed(self, gpio, level, tick):
        """Process switch change."""
        del tick
        self.machine.switch_controller.process_switch_by_num(str(gpio), not level, self)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                      eos_switch: SwitchSettings, coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> "DriverPlatformInterface":
        """Configure an output on the Raspberry Pi."""
        # disable pull up/down
        self.send_command(self.pi.set_pull_up_down(int(number), apigpio.PUD_OFF))
        # set output
        self.send_command(self.pi.set_mode(int(number), apigpio.OUTPUT))

        return RpiDriver(number, config, self)

    async def configure_i2c(self, number: str):
        """Configure I2c device."""
        device = RpiI2cDevice(number, self.machine.clock.loop, self)
        await device.open()
        return device
