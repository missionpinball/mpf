class DevicePositionMixin():
    @property
    def x(self):
        return self.config.get('x', None)

    @property
    def y(self):
        return self.config.get('y', None)

    @property
    def z(self):
        return self.config.get('z', None)
