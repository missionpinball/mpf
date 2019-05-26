"""Contains the Accelerometer device."""
import asyncio
import math
from typing import Tuple

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.machine import MachineController
from mpf.core.platform import AccelerometerPlatform
from mpf.core.system_wide_device import SystemWideDevice
from mpf.platforms.interfaces.accelerometer_platform_interface import AccelerometerPlatformInterface


@DeviceMonitor("value")
class Accelerometer(SystemWideDevice):

    """Implements a multi-axis accelerometer.

    In modern machines, accelerometers can be used for tilt detection and to
    detect whether a machine is properly leveled.

    The accelerometer device produces a data stream of readings which MPF
    converts to g-forces, and then events can be posted when the "hit" (or
    g-force) of an accelerometer exceeds a predefined threshold.

    """

    config_section = 'accelerometers'
    collection = 'accelerometers'
    class_label = 'accelerometer'

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise accelerometer.

        Args: Same as the Device parent class
        """
        self.platform = None        # type: AccelerometerPlatform
        super().__init__(machine, name)

        self.history = None     # type: Tuple[float, float, float]
        self.value = None       # type: Tuple[float, float, float]
        self.hw_device = None   # type: AccelerometerPlatformInterface

    @asyncio.coroutine
    def _initialize(self):
        """Initialise and configure accelerometer."""
        yield from super()._initialize()
        self.platform = self.machine.get_platform_sections(
            'accelerometers', self.config['platform'])

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Accelerometer must have a number.", 1)

        self.hw_device = self.platform.configure_accelerometer(self.config['number'],
                                                               self.config['platform_settings'], self)

    @classmethod
    def _calculate_vector_length(cls, x: float, y: float, z: float) -> float:
        return math.sqrt(x * x + y * y + z * z)

    # pylint: disable-msg=too-many-arguments
    def _calculate_angle(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
        dividor = (self._calculate_vector_length(x1, y1, z1) *
                   self._calculate_vector_length(x2, y2, z2))

        if dividor == 0:
            return 0

        return math.acos((x1 * x2 + y1 * y2 + z1 * z2) / dividor)

    def update_acceleration(self, x: float, y: float, z: float) -> None:
        """Calculate acceleration based on readings from hardware."""
        self.value = (x, y, z)

        if not self.history:
            self.history = (x, y, z)
            dx = dy = dz = 0
        else:
            dx = x - self.history[0]
            dy = y - self.history[1]
            dz = z - self.history[2]

            alpha = self.config['alpha']
            self.history = (self.history[0] * alpha + x * (1 - alpha),
                            self.history[1] * alpha + y * (1 - alpha),
                            self.history[2] * alpha + z * (1 - alpha))

        self._handle_hits(dx, dy, dz)
        # only check level when we are in a stedy state
        if math.fabs(dx) + math.fabs(dy) + math.fabs(dz) < 0.05:
            self._handle_level()

    def get_level_xyz(self) -> float:
        """Return current 3D level."""
        return self._calculate_angle(self.config['level_x'],
                                     self.config['level_y'],
                                     self.config['level_z'],
                                     self.value[0], self.value[1],
                                     self.value[2])

    def get_level_xz(self) -> float:
        """Return current 2D x/z level."""
        return self._calculate_angle(self.config['level_x'],
                                     0.0, self.config['level_z'],
                                     self.value[0], 0.0, self.value[2])

    def get_level_yz(self) -> float:
        """Return current 2D y/z level."""
        return self._calculate_angle(0.0,
                                     self.config['level_y'],
                                     self.config['level_z'],
                                     0.0, self.value[1], self.value[2])

    def _handle_level(self) -> None:

        deviation_xyz = self.get_level_xyz()
        deviation_xz = self.get_level_xz()
        deviation_yz = self.get_level_yz()

        for max_deviation in self.config['level_limits']:
            if deviation_xyz / math.pi * 180 > max_deviation:
                self.debug_log("Deviation x: %s, y: %s, total: %s",
                               deviation_xz / math.pi * 180,
                               deviation_yz / math.pi * 180,
                               deviation_xyz / math.pi * 180)
                self.machine.events.post(
                    self.config['level_limits'][max_deviation],
                    deviation_xyz=deviation_xyz,
                    deviation_xz=deviation_xz,
                    deviation_yz=deviation_yz)

    def _handle_hits(self, dx: float, dy: float, dz: float) -> None:
        acceleration = self._calculate_vector_length(dx, dy, dz)
        for min_acceleration in self.config['hit_limits']:
            if acceleration > min_acceleration:
                self.debug_log("Received hit of %s > %s. Posting %s",
                               acceleration,
                               min_acceleration,
                               self.config['hit_limits'][min_acceleration]
                               )
                self.machine.events.post(
                    self.config['hit_limits'][min_acceleration])
