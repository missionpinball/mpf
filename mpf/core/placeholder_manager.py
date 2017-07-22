"""Templates and placeholders."""
import ast
import operator as op
import abc
import re
from typing import TYPE_CHECKING

from mpf.core.mpf_controller import MpfController

if TYPE_CHECKING:   # pragma: no cover
    from mpf.core.machine import MachineController

# supported operators
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg, ast.Not: op.not_, ast.Mod: op.mod}

bool_operators = {ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b}

comparisons = {ast.Eq: op.eq, ast.Lt: op.lt, ast.Gt: op.gt, ast.LtE: op.le, ast.GtE: op.ge, ast.NotEq: op.ne}


class BaseTemplate(metaclass=abc.ABCMeta):

    """Base class for templates."""

    def __init__(self, template, placeholder_manger, default_value):
        """Initialise template."""
        self.template = template
        self.placeholder_manager = placeholder_manger
        self.default_value = default_value

    @abc.abstractmethod
    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template."""
        pass


class BoolTemplate(BaseTemplate):

    """Bool template."""

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template to bool."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except ValueError:
            if fail_on_missing_params:
                raise
            return self.default_value
        return bool(result)


class FloatTemplate(BaseTemplate):

    """Float template."""

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template to float."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except ValueError:
            if fail_on_missing_params:
                raise
            return self.default_value
        return float(result)


class IntTemplate(BaseTemplate):

    """Float template."""

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template to float."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except ValueError:
            if fail_on_missing_params:
                raise
            return self.default_value
        return int(result)


class StringTemplate(BaseTemplate):

    """String template."""

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template to string."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except ValueError:
            if fail_on_missing_params:
                raise
            return self.default_value
        return str(result)


class NativeTypeTemplate:

    """Native type template which encapsulates an int/float/bool."""

    def __init__(self, value):
        """Set value."""
        self.value = value

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Return value."""
        del parameters
        del fail_on_missing_params
        return self.value


class TextTemplate:

    """A simple text template."""

    var_finder = re.compile("(?<=\()[a-zA-Z_0-9|]+(?=\))")

    def __init__(self, machine: "MachineController", text: str) -> None:
        self.machine = machine
        self.text = text
        self.vars = self.var_finder.findall(text)
        self._change_callback = None

    def evaluate(self) -> str:
        """Evaluate placeholder to string."""
        return self._evaluate_text()

    def monitor_changes(self, callback):
        """Monitor variables for changes and call callback on changes."""
        self._change_callback = callback
        self._setup_variable_monitors()

    def stop_monitor(self):
        """Stop monitoring for changes."""
        self._change_callback = None
        self.machine.events.remove_handler(self._var_changes)

    def _add_player_var_handler(self, name: str) -> None:
        self.machine.events.add_handler('player_{}'.format(name), self._var_changes)

    def _add_current_player_handler(self) -> None:
        self.machine.events.add_handler('player_turn_started', self._var_changes)

    def _add_machine_var_handler(self, name: str) -> None:
        self.machine.events.add_handler('machine_var_{}'.format(name), self._var_changes)

    def _var_changes(self, **kwargs) -> None:
        del kwargs
        if self._change_callback:
            self._change_callback()

    def _setup_variable_monitors(self) -> None:
        for var_string in self.vars:
            if '|' not in var_string:
                self._add_player_var_handler(name=var_string)
                self._add_current_player_handler()
            else:
                source, variable_name = var_string.split('|')
                if source.lower().startswith('player'):

                    if source.lstrip('player'):  # we have player num
                        self._add_player_var_handler(name=variable_name)
                    else:  # no player num
                        self._add_player_var_handler(name=var_string)
                        self._add_current_player_handler()
                elif source.lower() == 'machine':
                    self._add_machine_var_handler(name=variable_name)

    def _evaluate_text(self) -> str:
        """Evaluate placeholder to string."""
        text = self.text
        for var_string in self.vars:
            if var_string.startswith('machine|'):
                _, var_name = var_string.split('|')
                if self.machine.is_machine_var(var_name):
                    replacement = str(self.machine.get_machine_var(var_name))
                else:
                    replacement = ''

                text = text.replace('(' + var_string + ')', replacement)

            elif self.machine.game and self.machine.game.player:
                if var_string.startswith('player|'):
                    text = text.replace('(' + var_string + ')',
                                        str(self.machine.game.player[var_string.split('|')[1]]))
                elif var_string.startswith('player') and '|' in var_string:
                    player_num, var_name = var_string.lstrip('player').split(
                            '|')
                    try:
                        value = self.machine.game.player_list[int(player_num) - 1][var_name]

                        if value is not None:
                            text = text.replace('(' + var_string + ')', str(value))
                        else:
                            text = text.replace('(' + var_string + ')', '')
                    except IndexError:
                        text = text.replace('(' + var_string + ')', '')
                elif self.machine.game.player.is_player_var(var_string):
                    value = self.machine.game.player[var_string]
                    if value is not None:
                        text = text.replace('(' + var_string + ')', str(value))
                    else:
                        text = text.replace('(' + var_string + ')', '')
            else:
                # set var to empty otherwise
                if var_string.startswith('player') or var_string.startswith('player') and '|' in var_string:
                    text = text.replace('(' + var_string + ')', '')

        return text


class DeviceClassPlaceholder:

    """Wrap a monitorable device."""

    def __init__(self, devices):
        """Initialise placeholder."""
        self._devices = devices

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    def __getattr__(self, item):
        """Attribute access."""
        device = self._devices.get(item)
        if not device:
            raise AssertionError("Device {} does not exist in placeholders.".format(item))

        return device.get_monitorable_state()


class DevicesPlaceholder:

    """Device monitor placeholder."""

    def __init__(self, machine):
        """Initialise placeholder."""
        self._machine = machine

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    def __getattr__(self, item):
        """Attribute access."""
        device = self._machine.device_manager.get_monitorable_devices().get(item)
        if not device:
            raise AssertionError("Device Collection {} not usable in placeholders.".format(item))
        return DeviceClassPlaceholder(device)


class ModeClassPlaceholder:

    """Wrap a mode."""

    def __init__(self, mode):
        """Initialise placeholder."""
        self._mode = mode

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    def __getattr__(self, item):
        """Attribute access."""
        this_item = getattr(self._mode, item)
        return this_item


class ModePlaceholder:

    """Mode placeholder."""

    def __init__(self, machine):
        """Initialise placeholder."""
        self._machine = machine

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    def __getattr__(self, item):
        """Attribute access."""
        if item not in self._machine.modes:
            raise ValueError("{} is not a valid mode name".format(item))

        return ModeClassPlaceholder(self._machine.modes[item])


class MachinePlaceholder:

    """Wraps the machine."""

    def __init__(self, machine):
        """Initialise placeholder."""
        self._machine = machine

    def __getitem__(self, item):
        """Array access."""
        return self._machine.get_machine_var(item)

    def __getattr__(self, item):
        """Attribute access."""
        return self._machine.get_machine_var(item)


class BasePlaceholderManager(MpfController):

    """Manages templates and placeholders for MPF and MC."""

    # needed here so the auto-detection of child classes works
    module_name = 'PlaceholderManager'
    config_name = 'placeholder_manager'

    def __init__(self, machine):
        """Initialise."""
        super().__init__(machine)
        self._eval_methods = {
            ast.Num: self._eval_num,
            ast.Str: self._eval_str,
            ast.NameConstant: self._eval_name_constant,
            ast.BinOp: self._eval_bin_op,
            ast.UnaryOp: self._eval_unary_op,
            ast.Compare: self._eval_compare,
            ast.BoolOp: self._eval_bool_op,
            ast.Attribute: self._eval_attribute,
            ast.Subscript: self._eval_subscript,
            ast.Name: self._eval_name,
            ast.IfExp: self._eval_if
        }

    @staticmethod
    def _parse_template(template_str):
        return ast.parse(template_str, mode='eval').body

    def _eval_subscript2(self, node, variables):
        if isinstance(node.slice, ast.Index):
            return self._eval(node.value, variables)[self._eval(node.slice.value, variables)]
        elif isinstance(node.slice, ast.Slice):
            return self._eval(node.value, variables)[self._eval(node.slice.lower, variables):
                                                     self._eval(node.slice.upper, variables):
                                                     self._eval(node.slice.step, variables)]
        else:
            raise TypeError(type(node))

    @staticmethod
    def _eval_num(node, variables):
        del variables
        return node.n

    @staticmethod
    def _eval_str(node, variables):
        del variables
        return node.s

    @staticmethod
    def _eval_name_constant(node, variables):
        del variables
        return node.value

    def _eval_if(self, node, variables):
        if self._eval(node.test, variables):
            return self._eval(node.body, variables)
        else:
            return self._eval(node.orelse, variables)

    def _eval_bin_op(self, node, variables):
        return operators[type(node.op)](self._eval(node.left, variables), self._eval(node.right, variables))

    def _eval_unary_op(self, node, variables):
        return operators[type(node.op)](self._eval(node.operand, variables))

    def _eval_compare(self, node, variables):
        if len(node.ops) > 1:
            raise AssertionError("Only single comparisons are supported.")
        try:
            return comparisons[type(node.ops[0])](self._eval(node.left, variables),
                                                  self._eval(node.comparators[0], variables))
        except TypeError as e:
            raise ValueError("Comparison failed: {}".format(e))

    def _eval_bool_op(self, node, variables):
        result = self._eval(node.values[0], variables)
        for i in range(1, len(node.values)):
            result = bool_operators[type(node.op)](result,
                                                   self._eval(node.values[i], variables))
        return result

    def _eval_attribute(self, node, variables):
        return getattr(self._eval(node.value, variables), node.attr)

    def _eval_subscript(self, node, variables):
        return self._eval_subscript2(node, variables)

    def _eval_name(self, node, variables):
        var = self.get_global_parameters(node.id)
        if var:
            return var
        elif node.id in variables:
            return variables[node.id]
        else:
            raise ValueError("Missing variable {}".format(node.id))

    def _eval(self, node, variables):
        if node is None:
            return None

        elif type(node) in self._eval_methods:  # pylint: disable-msg=unidiomatic-typecheck
            return self._eval_methods[type(node)](node, variables)
        else:
            raise TypeError(type(node))

    def build_float_template(self, template_str, default_value=0.0):
        """Build a float template from a string."""
        if isinstance(template_str, (float, int)):
            return NativeTypeTemplate(float(template_str))
        return FloatTemplate(self._parse_template(template_str), self, default_value)

    def build_int_template(self, template_str, default_value=0):
        """Build a int template from a string."""
        if isinstance(template_str, (float, int)):
            return NativeTypeTemplate(int(template_str))
        return IntTemplate(self._parse_template(template_str), self, default_value)

    def build_bool_template(self, template_str, default_value=False):
        """Build a bool template from a string."""
        if isinstance(template_str, bool):
            return NativeTypeTemplate(template_str)
        return BoolTemplate(self._parse_template(template_str), self, default_value)

    def build_string_template(self, template_str, default_value=""):
        """Build a string template from a string."""
        return StringTemplate(self._parse_template(template_str), self, default_value)

    def get_global_parameters(self, name):
        """Return global params."""
        raise NotImplementedError()

    def evaluate_template(self, template, parameters):
        """Evaluate template."""
        return self._eval(template, parameters)


class PlaceholderManager(BasePlaceholderManager):

    """Manages templates and placeholders for MPF."""

    # pylint: disable-msg=too-many-return-statements
    def get_global_parameters(self, name):
        """Return global params."""
        if name == "settings":
            return self.machine.settings
        elif name == "machine":
            return MachinePlaceholder(self.machine)
        elif name == "device":
            return DevicesPlaceholder(self.machine)
        elif name == "mode":
            return ModePlaceholder(self.machine)
        elif self.machine.game:
            if name == "current_player":
                return self.machine.game.player
            elif name == "players":
                return self.machine.game.player_list
            elif name == "game":
                return self.machine.game
        return False
