"""Device Mixins."""
from typing import List


class DevicePositionMixin():

    """Adds x/y/z getters to a device.

    For devices that have x/y/z config in the yaml this
    mixin will add getters to allow the use of device.x
    device.y and device.z instead of device.config['x']
    """

    __slots__ = []  # type: List[str]

    @property
    def x(self):
        """Get the X value from the config.

        Returns the devices x position from config
        """
        return self.config.get('x', None)

    @property
    def y(self):
        """Get the Y value from the config.

        Returns the devices y position from config
        """
        return self.config.get('y', None)

    @property
    def z(self):
        """Get the Z value from the config.

        Returns the devices z position from config
        """
        return self.config.get('z', None)
