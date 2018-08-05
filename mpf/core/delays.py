"""Contains the DelayManager and DelayManagerRegistry base classes."""

import uuid
from functools import partial

from typing import Any, Callable, Dict, Set

from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController

__api__ = ['DelayManager', 'DelayManagerRegistry']


class DelayManagerRegistry:

    """Keeps references to all DelayManager instances."""

    __slots__ = ["delay_managers", "machine"]

    def __init__(self, machine: "MachineController") -> None:
        """Initialise delay registry."""
        self.delay_managers = set()     # type: Set["DelayManager"]
        self.machine = machine

    def add_delay_manager(self, delay_manager: "DelayManager") -> None:
        """Add a delay manager to the list.

        Args:
            delay_manager: The :class:`DelayManager` instance you're adding to
                this registry.

        """
        self.delay_managers.add(delay_manager)


class DelayManager(MpfController):

    """Handles delays for one object.

    By default, a machine-wide instance is created and available via
    ``self.machine.delay``.

    Individual modes also have Delay Managers which can be accessed in
    mode code via ``self.delay``. (Delays in mode-based delay managers
    are automatically removed when the mode stops.)

    """

    __slots__ = ["delays", "registry"]

    config_name = "delay_manager"

    def __init__(self, registry: DelayManagerRegistry) -> None:
        """Initialise delay manager."""
        self.delays = {}        # type: Dict[str, Any]
        super().__init__(registry.machine)
        self.registry = registry
        self.registry.add_delay_manager(self)

    def add(self, ms: int, callback: Callable[..., None], name: str = None,
            **kwargs) -> str:
        """Add a delay.

        Args:
            ms: The number of milliseconds you want this delay to be for.
            callback: The method that is called when this delay ends.
            name: String name of this delay. This name is arbitrary and only
                used to identify the delay later if you want to remove or
                change it. If you don't provide it, a UUID4 name will be
                created.
            **kwargs: Any other (optional) kwarg pairs you pass will be
                passed along as kwargs to the callback method.

        Returns:
            String name or UUID4 of the delay which you can use to remove it
            later.
        """
        if not name:
            name = str(uuid.uuid4())
        self.debug_log("Adding delay. Name: '%s' ms: %s, callback: %s, "
                       "kwargs: %s", name, ms, callback, kwargs)

        if name in self.delays:
            self.machine.clock.unschedule(self.delays[name])
            del self.delays[name]

        self.delays[name] = self.machine.clock.schedule_once(
            partial(self._process_delay_callback, name, callback, **kwargs),
            ms / 1000.0)

        return name

    def remove(self, name: str):
        """Remove a delay by name.

        Removing a delay prevents the callback from being called and cancels
        the delay.

        Args:
            name: String name of the delay you want to remove. If there is no
                delay with this name, that's ok. Nothing happens.
        """
        self.debug_log("Removing delay: '%s'", name)
        if name in self.delays:
            self.machine.clock.unschedule(self.delays[name])
            try:
                del self.delays[name]
            except KeyError:
                pass

    def add_if_doesnt_exist(self, ms: int, callback: Callable[..., None],
                            name: str, **kwargs) -> str:
        """Add a delay only if a delay with that name doesn't exist already.

        Args:
            ms: Int of the number of milliseconds you want this delay to be
                for.
            callback: The method that is called when this delay ends.
            name: String name of this delay. This name is arbitrary and only
                used to identify the delay later if you want to remove or
                change it.
            **kwargs: Any other (optional) kwarg pairs you pass will be
                passed along as kwargs to the callback method.

        Returns:
            String name of the delay which you can use to remove it later.
        """
        if not self.check(name):
            return self.add(ms, callback, name, **kwargs)
        else:
            return name

    def check(self, delay: str) -> bool:
        """Check to see if a delay exists.

        Args:
            delay: A string of the delay you're checking for.

        Returns:
            True if the delay exists. False otherwise.
        """
        return delay in self.delays

    def reset(self, ms: int, callback: Callable[..., None], name: str,
              **kwargs) -> str:
        """Reset a delay.

        Resetting will first delete the existing delay (if it exists) and then
        add new delay with the new settings. If the delay does not exist,
        that's ok, and this method is essentially the same as just adding a
        delay with this name.

        Args:
            ms: The number of milliseconds you want this delay to be for.
            callback: The method that is called when this delay ends.
            name: String name of this delay. This name is arbitrary and only
                used to identify the delay later if you want to remove or
                change it. If you don't provide it, a UUID4 name will be
                created.
            **kwargs: Any other (optional) kwarg pairs you pass will be
                passed along as kwargs to the callback method.

        Returns:
            String name or UUID4 of the delay which you can use to remove it
            later.
        """
        if name in self.delays:
            self.remove(name)

        return self.add(ms, callback, name, **kwargs)

    def clear(self) -> None:
        """Remove (clear) all the delays associated with this DelayManager."""
        for name in list(self.delays.keys()):
            self.machine.clock.unschedule(self.delays[name])
            self.remove(name)

        self.delays = {}

    def run_now(self, name: str):
        """Run a delay callback now instead of waiting until its time comes.

        This will cancel the future running of the delay callback.

        Args:
            name: Name of the delay to run. If this name is not an active
                delay, that's fine. Nothing happens.
        """
        if name in self.delays:
            try:
                # have to save the callback ref first, since if the callback
                # schedules a new delay with the same name, then the removal
                # will remove it
                # pylint: disable-msg=protected-access
                cb = self.delays[name]._callback
                self.remove(name)
                cb()
            except KeyError:
                pass

    def _process_delay_callback(self, name: str, callback: Callable[..., None], **kwargs):
        # Process the delay callback and run the event queue afterwards
        self.debug_log("---Processing delay: %s", name)
        try:
            del self.delays[name]
        except KeyError:
            pass
        callback(**kwargs)
        self.machine.events.process_event_queue()
