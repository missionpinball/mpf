import abc


class SwitchPlatformInterface(metaclass=abc.ABCMeta):
    """
    SwitchPlatformInterface is an abstract base class that should be overridden for all
    switches interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support switch operations in MPF.
    """

    def __init__(self, config, number):
        self.config = config
        self.number = number
