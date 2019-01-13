"""StepStick or similar stepper driver connected to a digital output."""
import asyncio
from typing import Optional

import logging

from mpf.devices.digital_output import DigitalOutput

from mpf.core.platform import StepperPlatform
from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface


class DigitalOutputStepStickStepper(StepperPlatformInterface):

    """Stepper on a digital output driven by a StepStick."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, platform, direction_output, step_output, enable_output, number, config):
        """Initialize stepper."""
        self.platform = platform
        self.number = number
        self._move_complete = asyncio.Event(loop=self.platform.machine.clock.loop)
        self._move_complete.set()
        self._move_task = None
        self.config = config
        self.direction_output = direction_output    # type: DigitalOutput
        self.step_output = step_output              # type: DigitalOutput
        self.enable_output = enable_output          # type: Optional[DigitalOutput]

        if self.enable_output:
            self.enable_output.enable()

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def move_rel_pos(self, position):
        """Move a number of steps in one direction."""
        if self._move_task and not self._move_task.done():
            raise AssertionError("Last move has not been completed. Calls stop first.")
        self._move_complete.clear()
        self._move_task = self.platform.machine.clock.loop.create_task(self._move_pos(position))
        self._move_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _move_pos(self, steps):
        if steps > 0:
            self.direction_output.enable()
        else:
            self.direction_output.disable()
        for _ in range(int(abs(steps))):
            self.step_output.enable()
            yield from asyncio.sleep(self.config['high_time'], loop=self.platform.machine.clock.loop)
            self.step_output.disable()
            yield from asyncio.sleep(self.config['low_time'], loop=self.platform.machine.clock.loop)

        self._move_complete.set()

    def move_vel_mode(self, velocity):
        """Move at a certain speed."""
        if velocity == 0:
            self.stop()
        else:
            if self._move_task and not self._move_task.done():
                self._move_task.cancel()
            self._move_complete.clear()
            self._move_task = self.platform.machine.clock.loop.create_task(self._move_rel(velocity))
            self._move_task.add_done_callback(self._done)

    @asyncio.coroutine
    def _move_rel(self, velocity):
        if velocity > 0:
            self.direction_output.enable()
        else:
            self.direction_output.disable()
        while True:
            self.step_output.enable()
            yield from asyncio.sleep(self.config['high_time'] * abs(velocity), loop=self.platform.machine.clock.loop)
            self.step_output.disable()
            yield from asyncio.sleep(self.config['low_time'] * abs(velocity), loop=self.platform.machine.clock.loop)
        # this will never complete. you need to call stop

    def stop(self):
        """Stop movements."""
        if self._move_task:
            self._move_task.cancel()
            self._move_task = None
        self.step_output.disable()
        self._move_complete.set()

    def home(self, direction):
        """Not implemented."""
        self.platform.raise_config_error("Please use homing_mode switch", 5, context=self.number)

    def wait_for_move_completed(self):
        """Wait for move complete."""
        return self._move_complete.wait()


class StepStickDigitalOutputPlatform(StepperPlatform):

    """Drive a stepper using a StepStick controller on a digital output."""

    def __init__(self, machine):
        """Initialize platform."""
        super().__init__(machine)
        self.log = logging.getLogger('StepStick')

    @classmethod
    def get_stepper_config_section(cls):
        """Return config section."""
        return "step_stick_stepper_settings"

    @asyncio.coroutine
    def configure_stepper(self, number: str, config: dict) -> "StepperPlatformInterface":
        """Configure a stepper driven by StepStick on a digital output."""
        try:
            direction_output_str, step_output_str, enable_output_str = number.split(":")
        except IndexError:
            enable_output_str = False
            try:
                direction_output_str, step_output_str = number.split(":")
            except IndexError:
                return self.raise_config_error("Number for step_stick steppers needs to be "
                                               "direction_output:step_output or "
                                               "direction_output:step_output:enable_output but is {}".format(number),
                                               1)

        try:
            direction_output = self.machine.digital_outputs[direction_output_str]
        except IndexError:
            return self.raise_config_error("direction_output {} does not exist".format(direction_output_str), 2)

        try:
            step_output = self.machine.digital_outputs[step_output_str]
        except IndexError:
            return self.raise_config_error("step_output {} does not exist".format(step_output_str), 3)

        if enable_output_str:
            try:
                enable_output = self.machine.digital_outputs[enable_output_str]
            except IndexError:
                return self.raise_config_error("enable_output {} does not exist".format(enable_output_str), 4)
        else:
            enable_output = None

        stepper = DigitalOutputStepStickStepper(self, direction_output, step_output, enable_output, number, config)
        return stepper
