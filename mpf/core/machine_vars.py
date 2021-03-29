"""Contains the MachineVariables class."""

import copy
from platform import platform, python_version, system, release, version, system_alias, machine as platform_machine
from typing import Any, Dict, Optional

from mpf._version import version as mpf_version, extended_version as mpf_extended_version
from mpf.core.data_manager import DataManager
from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class MachineVariables(LogMixin):

    """Class for Machine Variables."""

    __slots__ = ["machine", "machine_vars", "machine_var_monitor", "machine_var_data_manager"]

    def __init__(self, machine) -> None:
        """Initialize machine controller."""
        super().__init__()

        self.machine = machine              # type: MachineController
        self.machine_vars = dict()          # type: Dict[str, Any]
        self.machine_var_monitor = False
        self.machine_var_data_manager = None    # type: Optional[DataManager]
        self.configure_logging("machine_vars", self.machine.config['logging']['console']['machine_vars'],
                               self.machine.config['logging']['file']['machine_vars'])

    def load_machine_vars(self, machine_var_data_manager: DataManager, current_time) -> None:
        """Load machine vars from data manager."""
        self.machine_var_data_manager = machine_var_data_manager

        for name, settings in (
                iter(self.machine_var_data_manager.get_data().items())):

            if not isinstance(settings, dict) or "value" not in settings:
                continue

            if ('expire' in settings and settings['expire'] and
                    settings['expire'] < current_time):

                continue

            self.set_machine_var(name=name, value=settings['value'])

        self._load_initial_machine_vars()

        # Create basic system information machine variables
        self.set_machine_var(name="mpf_version", value=mpf_version)
        '''machine_var: mpf_version

        desc: Full version string for MPF.
        '''
        self.set_machine_var(name="mpf_extended_version", value=mpf_extended_version)
        '''machine_var: mpf_extended_version

        desc: Extended version string for MPF. Contains show and bcp version as well.
        '''
        self.set_machine_var(name="python_version", value=python_version())
        '''machine_var: python_version

        desc: Python version.
        '''
        self.set_machine_var(name="platform", value=platform(aliased=True))
        '''machine_var: platform

        desc: A single string identifying the underlying platform
              with as much useful information as possible.
        '''
        platform_info = system_alias(system(), release(), version())
        self.set_machine_var(name="platform_system", value=platform_info[0])
        '''machine_var: platform_system

        desc: Your system (Linux/Windows/Mac).
        '''
        self.set_machine_var(name="platform_release", value=platform_info[1])
        '''machine_var: platform_release

        desc: Release of your operating system.
        '''
        self.set_machine_var(name="platform_version", value=platform_info[2])
        '''machine_var: platform_version

        desc: Version of your operating system.
        '''
        self.set_machine_var(name="platform_machine", value=platform_machine())
        '''machine_var: platform_machine

        desc: Architecture of your machine (32bit/64bit).
        '''

    def __getitem__(self, key):
        """Allow the user to access a machine variable with []. This would be used is machine.variables["var_name"]."""
        return self.get_machine_var(key)

    def __setitem__(self, key, value):
        """Allow the user to set a machine variable with []. Used as machine.variables["var_name"] = value."""
        return self.set_machine_var(key, value)

    def get(self, key):
        """Allow the user to get a machine variable with .get ."""
        return self.get_machine_var(key)

    def _load_initial_machine_vars(self) -> None:
        """Load initial machine var values from config if they did not get loaded from data."""
        if 'machine_vars' not in self.machine.config:
            return

        config = self.machine.config['machine_vars']
        for name, element in config.items():
            if name not in self.machine_vars:
                element = self.machine.config_validator.validate_config("machine_vars", copy.deepcopy(element))
                self.set_machine_var(name=name,
                                     value=Util.convert_to_type(element['initial_value'], element['value_type']))
            self.configure_machine_var(name=name, persist=element.get('persist', False))

    def _write_machine_var_to_disk(self, name: str) -> None:
        """Write value to disk."""
        if self.machine_vars[name]['persist'] and self.machine.config['mpf']['save_machine_vars_to_disk']:
            self._write_machine_vars_to_disk()

    def _write_machine_vars_to_disk(self):
        """Update machine vars on disk."""
        self.machine_var_data_manager.save_all(
            {name: {"value": var["value"], "expire": var['expire_secs']}
             for name, var in self.machine_vars.items() if var["persist"]})

    def get_machine_var(self, name: str) -> Any:
        """Return the value of the variable if it exists, or None if the variable does not exist.

        Args:
        ----
            name: String name of the variable you want to get that value for.
        """
        try:
            return self.machine_vars[name]['value']
        except KeyError:
            return None

    def is_machine_var(self, name: str) -> bool:
        """Return true if machine variable exists."""
        return name in self.machine_vars

    def configure_machine_var(self, name: str, persist: bool, expire_secs: int = None) -> None:
        """Create a new machine variable.

        Args:
        ----
            name: String name of the variable.
            persist: Boolean as to whether this variable should be saved to
                disk so it's available the next time MPF boots.
            expire_secs: Optional number of seconds you'd like this variable
                to persist on disk for. When MPF boots, if the expiration time
                of the variable is in the past, it will not be loaded.
                For example, this lets you write the number of credits on
                the machine to disk to persist even during power off, but you
                could set it so that those only stay persisted for an hour.
        """
        if name not in self.machine_vars:
            self.machine_vars[name] = {'value': None, 'persist': persist, 'expire_secs': expire_secs}
        else:
            self.machine_vars[name]['persist'] = persist
            self.machine_vars[name]['expire_secs'] = expire_secs

    def set_machine_var(self, name: str, value: Any) -> None:
        """Set the value of a machine variable.

        Args:
        ----
            name: String name of the variable you're setting the value for.
            value: The value you're setting. This can be any Type.
        """
        if name not in self.machine_vars:
            self.configure_machine_var(name=name, persist=False)
            prev_value = None
            change = True
        else:
            prev_value = self.machine_vars[name]['value']
            try:
                change = value - prev_value
            except TypeError:
                change = prev_value != value

        # set value
        self.machine_vars[name]['value'] = value

        if change:
            self._write_machine_var_to_disk(name)

            self.debug_log("Setting machine_var '%s' to: %s, (prior: %s, "
                           "change: %s)", name, value, prev_value,
                           change)
            self.machine.events.post('machine_var_' + name,
                                     value=value,
                                     prev_value=prev_value,
                                     change=change)
            '''event: machine_var_(name)
            config_section: machine_vars
            class_label: machine_var

            desc: Posted when a machine variable is added or changes value.
            (Machine variables are like player variables, except they're
            maintained machine-wide instead of per-player or per-game.)

            args:

            value: The new value of this machine variable.

            prev_value: The previous value of this machine variable, e.g. what
            it was before the current value.

            change: If the machine variable just changed, this will be the
            amount of the change. If it's not possible to determine a numeric
            change (for example, if this machine variable is a list), then this
            *change* value will be set to the boolean *True*.
            '''

            if self.machine_var_monitor:
                for callback in self.machine.monitors['machine_vars']:
                    callback(name=name, value=value,
                             prev_value=prev_value, change=change)

    def remove_machine_var(self, name: str) -> None:
        """Remove a machine variable by name.

        If this variable persists to disk, it will remove it from there too.

        Args:
        ----
            name: String name of the variable you want to remove.
        """
        try:
            prev_value = self.machine_vars[name]
            del self.machine_vars[name]
            self._write_machine_vars_to_disk()
        except KeyError:
            pass
        else:
            if self.machine_var_monitor:
                for callback in self.machine.monitors['machine_vars']:
                    callback(name=name, value=None,
                             prev_value=prev_value, change=True)

    def remove_machine_var_search(self, startswith: str = '', endswith: str = '') -> None:
        """Remove a machine variable by matching parts of its name.

        Args:
        ----
            startswith: Optional start of the variable name to match.
            endswith: Optional end of the variable name to match.

        For example, if you pass startswit='player' and endswith='score', this
        method will match and remove player1_score, player2_score, etc.
        """
        for var in list(self.machine_vars.keys()):
            if var.startswith(startswith) and var.endswith(endswith):
                del self.machine_vars[var]

        self._write_machine_vars_to_disk()
