"""Platform interface for smart steppers."""
import abc


class StepperPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for smart steppers in hardware platforms.

    Smart steppers is being used here to designate axis controllers that add motion control over the top of a regular
    direction and step type interface. Including homing, positioning, and velocity modes.

    StepperPlatformInterface is an abstract base class that should be overridden for all
    smart stepper/axis interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support smart stepper operations in MPF.
    """

    @abc.abstractmethod
    def home(self):
        """Home an axis, resetting 0 position."""
        raise NotImplementedError

    @abc.abstractmethod
    def move_abs_pos(self, position):
        """Move axis to a certain absolute position."""
        raise NotImplementedError

    @abc.abstractmethod
    def move_rel_pos(self, position):
        """Move axis to a relative position."""
        raise NotImplementedError

    @abc.abstractmethod
    def move_vel_mode(self, velocity):
        """Move at a specific velocity (pos = clockwise, neg = counterclockwise)."""
        raise NotImplementedError

    @abc.abstractmethod
    def current_position(self):
        """Return the current position of the stepper."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self):
        """Stop a motor."""
        raise NotImplementedError
