"""Platform to control the hardware of a Raspberry Pi."""
import asyncio
from typing import Optional, Dict, Any

from mpf.platforms.interfaces.i2c_platform_interface import I2cPlatformInterface

from mpf.core.delays import DelayManager

from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.core.platform import SwitchPlatform, DriverPlatform, ServoPlatform, SwitchSettings, \
    DriverSettings, DriverConfig, SwitchConfig, I2cPlatform

# apiogpio is not a requirement for MPF so we fail with a nice error when loading
try:
    import apigpio
except ImportError:
    apigpio = None


class RpiSwitch(SwitchPlatformInterface):

    """A switch on a RPI."""

    def get_board_name(self):
        """Return name."""
        return "Raspberry Pi"


class RpiDriver(DriverPlatformInterface):

    """An output on a Rasoberry Pi."""

    def __init__(self, number, config, platform):
        """Initialise output."""
        super().__init__(config, number)
        self.platform = platform            # type: RaspberryPiHardwarePlatform
        self.gpio = int(self.number)
        self.delay = DelayManager(self.platform.machine)

    def get_board_name(self):
        """Return name."""
        return "Raspberry Pi"

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse output."""
        self.enable(pulse_settings, None)

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
        """Initialise servo."""
        self.gpio = int(number)
        self.platform = platform    # type: RaspberryPiHardwarePlatform

    def go_to_position(self, position):
        """Move servo to position."""
        # can be between 1000 and 2000us
        position_translated = 1000 + position * 1000
        self.platform.send_command(self.platform.pi.set_servo_pulsewidth(self.gpio, position_translated))

    @classmethod
    def set_speed_limit(cls, speed_limit):
        """Todo emulate speed parameter."""
        pass

    @classmethod
    def set_acceleration_limit(cls, acceleration_limit):
        """Todo emulate acceleration parameter."""
        pass


class RpiI2cDevice(I2cPlatformInterface):

    """A I2c device on a Rpi."""

    def __init__(self, number: str, loop, platform) -> None:
        """Initialise i2c device on rpi."""
        super().__init__(number)
        self.loop = loop
        self.pi = platform.pi
        self.platform = platform
        self.number = number
        self.handle = None

    @asyncio.coroutine
    def open(self):
        """Open I2c port."""
        self.handle = yield from self._get_i2c_handle(self.number)

    @staticmethod
    def _get_i2c_bus_address(address):
        """Split and return bus + address."""
        if isinstance(address, int):
            return 0, address
        bus, address = address.split("-")
        return int(bus), int(address)

    @asyncio.coroutine
    def _get_i2c_handle(self, address):
        """Get or open handle for i2c device via pigpio."""
        bus_address, device_address = self._get_i2c_bus_address(address)
        handle = yield from self.pi.i2c_open(bus_address, device_address)
        return handle

    def i2c_write8(self, register, value):
        """Write to i2c via pigpio."""
        self.platform.send_command(self._i2c_write8_async(register, value))

    @asyncio.coroutine
    def _i2c_write8_async(self, register, value):
        yield from self.pi.i2c_write_byte_data(self.handle, register, value)

    @asyncio.coroutine
    def i2c_read8(self, register):
        """Read from i2c via pigpio."""
        return (yield from self.pi.i2c_read_byte_data(self.handle, register))

    @asyncio.coroutine
    def i2c_read_block(self, register, count):
        """Read block via I2C."""
        data = yield from self.pi.i2c_read_i2c_block_data(self.handle, register, count)
        return data


class RaspberryPiHardwarePlatform(SwitchPlatform, DriverPlatform, ServoPlatform, I2cPlatform):

    """Control the hardware of a Raspberry Pi.

    Works locally and remotely via network.
    """

    def __init__(self, machine):
        """Initialise Raspberry Pi platform."""
        super().__init__(machine)

        if not apigpio:
            raise AssertionError("To use the Raspberry Pi platform you need to install the apigpio extension.")

        self.pi = None          # type: apigpio.Pi
        # load config
        self.config = self.machine.config_validator.validate_config("raspberry_pi", self.machine.config['raspberry_pi'])
        self._switches = None   # type: int

        self._cmd_queue = None  # type: asyncio.Queue
        self._cmd_task = None   # type: asyncio.Task
        self._configure_device_logging_and_debug("Raspberry Pi", self.config)

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        # create pi object and connect
        self.pi = apigpio.Pi(self.machine.clock.loop)
        yield from self.pi.connect((self.config['ip'], self.config['port']))

        self._switches = yield from self.pi.read_bank_1()

        self._cmd_queue = asyncio.Queue(loop=self.machine.clock.loop)
        self._cmd_task = self.machine.clock.loop.create_task(self._run())
        self._cmd_task.add_done_callback(self._done)

    def send_command(self, cmd):
        """Add a command to the command queue."""
        self._cmd_queue.put_nowait(cmd)

    @asyncio.coroutine
    def _run(self):
        """Handle the command queue."""
        while True:
            # get next command
            cmd = yield from self._cmd_queue.get()
            # run command
            yield from cmd

    def stop(self):
        """Stop platform."""
        if self._cmd_task:
            self._cmd_task.cancel()
            self._cmd_task = None

        if self.pi:
            self.machine.clock.loop.run_until_complete(self.pi.stop())
            self.pi = None

    @staticmethod
    def _done(future):  # pragma: no cover
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def configure_servo(self, number: str) -> ServoPlatformInterface:
        """Configure a servo."""
        return RpiServo(number, self)

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Return current switch states."""
        hw_states = dict()
        curr_bit = 1
        for index in range(32):
            hw_states[str(index)] = (curr_bit & self._switches) == 0
            curr_bit <<= 1
        return hw_states

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure a switch with pull up."""
        # set input
        self.send_command(self.pi.set_mode(int(number), apigpio.INPUT))
        # configure pull up
        self.send_command(self.pi.set_pull_up_down(int(number), apigpio.PUD_UP))

        # if config.debounce:
        #     # configure debounce to 2ms
        #     self.send_command(self.pi.set_glitch_filter(int(number), 2000))
        # else:
        #     # configure debounce to 100us
        #     self.send_command(self.pi.set_glitch_filter(int(number), 100))

        # add callback
        self.send_command(self.pi.add_callback(int(number), apigpio.EITHER_EDGE, self._switch_changed))

        return RpiSwitch(config, number)

    def _switch_changed(self, gpio, level, tick):
        """Process switch change."""
        del tick
        self.machine.switch_controller.process_switch_by_num(str(gpio), level, self)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Raise exception."""
        raise AssertionError("Not supported on the RPi currently. Write in the forum if you need it.")

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
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

    @asyncio.coroutine
    def configure_i2c(self, number: str):
        """Configure I2c device."""
        device = RpiI2cDevice(number, self.machine.clock.loop, self)
        yield from device.open()
        return device
