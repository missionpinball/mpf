"""Contains the Accelerometer device."""

import math

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("value")
class Accelerometer(SystemWideDevice):

    """Implement an accelerometer.

    Args: Same as the Device parent class

    """

    config_section = 'accelerometers'
    collection = 'accelerometers'
    class_label = 'accelerometer'

    def __init__(self, machine, name):
        """Initialise accelerometer."""
        super().__init__(machine, name)

        self.history = None
        self.value = None
        self.hw_device = None

    def _initialize(self):
        self.load_platform_section('accelerometers')
        self.hw_device = self.platform.configure_accelerometer(self.config, self)

    @classmethod
    def _calculate_vector_length(cls, x, y, z):
        return math.sqrt(x * x + y * y + z * z)

    # pylint: disable-msg=too-many-arguments
    def _calculate_angle(self, x1, y1, z1, x2, y2, z2):
        dividor = (self._calculate_vector_length(x1, y1, z1) *
                   self._calculate_vector_length(x2, y2, z2))

        if dividor == 0:
            return 0

        return math.acos((x1 * x2 + y1 * y2 + z1 * z2) / dividor)

    def update_acceleration(self, x, y, z):
        """Calculate acceleration based on readings from hardware."""
        self.value = (x, y, z)

        if not self.history:
            self.history = (x, y, z)
            dx = dy = dz = 0
        else:
            dx = x - self.history[0]
            dy = y - self.history[1]
            dz = z - self.history[2]

            alpha = 0.95
            self.history = (self.history[0] * alpha + x * (1 - alpha),
                            self.history[1] * alpha + y * (1 - alpha),
                            self.history[2] * alpha + z * (1 - alpha))

        self._handle_hits(dx, dy, dz)
        self._handle_level()

    def get_level_xyz(self):
        """Return current 3D level."""
        return self._calculate_angle(self.config['level_x'],
                                     self.config['level_y'],
                                     self.config['level_z'],
                                     self.value[0], self.value[1],
                                     self.value[2])

    def get_level_xz(self):
        """Return current 2D x/z level."""
        return self._calculate_angle(self.config['level_x'],
                                     0.0, self.config['level_z'],
                                     self.value[0], 0.0, self.value[2])

    def get_level_yz(self):
        """Return current 2D y/z level."""
        return self._calculate_angle(0.0,
                                     self.config['level_y'],
                                     self.config['level_z'],
                                     0.0, self.value[1], self.value[2])

    def _handle_level(self):
        deviation_xyz = self.get_level_xyz()
        deviation_xz = self.get_level_xz()
        deviation_yz = self.get_level_yz()

        for max_deviation in self.config['level_limits']:
            if deviation_xyz / math.pi * 180 > max_deviation:
                self.log.debug("Deviation x: %s, y: %s, total: %s",
                               deviation_xz / math.pi * 180,
                               deviation_yz / math.pi * 180,
                               deviation_xyz / math.pi * 180)
                self.machine.events.post(
                    self.config['level_limits'][max_deviation],
                    deviation_xyz=deviation_xyz,
                    deviation_xz=deviation_xz,
                    deviation_yz=deviation_yz)

    def _handle_hits(self, dx, dy, dz):
        acceleration = self._calculate_vector_length(dx, dy, dz)
        for min_acceleration in self.config['hit_limits']:
            if acceleration > min_acceleration:
                self.log.debug("Received hit of %s > %s. Posting %s",
                               acceleration,
                               min_acceleration,
                               self.config['hit_limits'][min_acceleration]
                               )
                self.machine.events.post(
                    self.config['hit_limits'][min_acceleration])
