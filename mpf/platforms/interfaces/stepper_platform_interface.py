"""Platform interface for smart steppers."""
import abc
import asyncio


class StepperPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for smart steppers in hardware platforms.

    Smart steppers is being used here to designate axis controllers that add motion control over the top of a regular
    direction and step type interface. Including homing, positioning, and velocity modes.

    StepperPlatformInterface is an abstract base class that should be overridden for all
    smart stepper/axis interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support smart stepper operations in MPF.
    """

    __slots__ = []

    @abc.abstractmethod
    def home(self, direction):
        """Home an axis, resetting 0 position.

        direction can be clockwise or counterclockwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def wait_for_move_completed(self):
        """Return after the last move completed.

        This is also used to check if homing is completed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def move_rel_pos(self, position):
        """Move axis to a certain relative position."""
        raise NotImplementedError

    @abc.abstractmethod
    def move_vel_mode(self, velocity):
        """Move at a specific velocity (pos = clockwise, neg = counterclockwise)."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self):
        """Stop the stepper."""
        raise NotImplementedError

    def set_home_position(self):
        """Tell the hardware that it reached the home position."""
        pass
