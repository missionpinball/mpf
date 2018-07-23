"""Templates and placeholders."""
import ast
import string
import asyncio
import operator as op
import abc
import re
from typing import Tuple, List, Any

from mpf.core.utility_functions import Util

from mpf.core.mpf_controller import MpfController

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController


# supported operators
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg, ast.Not: op.not_, ast.Mod: op.mod}

bool_operators = {ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b}

comparisons = {ast.Eq: op.eq, ast.Lt: op.lt, ast.Gt: op.gt, ast.LtE: op.le, ast.GtE: op.ge, ast.NotEq: op.ne}


class TemplateEvalError(Exception):

    """An error occurred during a template evaluation."""

    def __init__(self, subscriptions):
        """Remember subscriptions."""
        super().__init__(subscriptions)
        self.subscriptions = subscriptions

    def __str__(self):
        """Return description."""
        return "<TemplateEvalError with subscriptions {}>".format(self.subscriptions)


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
        raise NotImplementedError


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
        except TemplateEvalError:
            return self.default_value
        return bool(result)

    def evaluate_and_subscribe(self, parameters) -> Tuple[bool, asyncio.Future]:
        """Evaluate template to bool and subscribe."""
        result, subscriptions = self.placeholder_manager.evaluate_and_subscribe_template(self.template, parameters)
        if isinstance(result, TemplateEvalError):
            result = self.default_value
        return bool(result), subscriptions


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
        except TemplateEvalError:
            return self.default_value
        return float(result)

    def evaluate_and_subscribe(self, parameters) -> Tuple[float, asyncio.Future]:
        """Evaluate template to float and subscribe."""
        result, subscriptions = self.placeholder_manager.evaluate_and_subscribe_template(self.template, parameters)
        if isinstance(result, TemplateEvalError):
            result = self.default_value

        return float(result), subscriptions


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
        except TemplateEvalError:
            return self.default_value
        return int(result)

    def evaluate_and_subscribe(self, parameters) -> Tuple[int, asyncio.Future]:
        """Evaluate template to int and subscribe."""
        result, subscriptions = self.placeholder_manager.evaluate_and_subscribe_template(self.template, parameters)
        if isinstance(result, TemplateEvalError):
            result = self.default_value
        return int(result), subscriptions


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


class RawTemplate(BaseTemplate):

    """Raw template."""

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except (ValueError, IndexError):
            if fail_on_missing_params:
                raise
            return self.default_value
        return result

    def evaluate_and_subscribe(self, parameters) -> Tuple[bool, asyncio.Future]:
        """Evaluate template to bool and subscribe."""
        result, subscriptions = self.placeholder_manager.evaluate_and_subscribe_template(self.template, parameters)
        if isinstance(result, TemplateEvalError):
            result = self.default_value
        return result, subscriptions


class NativeTypeTemplate:

    """Native type template which encapsulates an int/float/bool."""

    def __init__(self, value, machine):
        """Set value."""
        self.value = value
        self.machine = machine

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Return value."""
        del parameters
        del fail_on_missing_params
        return self.value

    def evaluate_and_subscribe(self, parameters) -> Tuple[int, asyncio.Future]:
        """Evaluate and subscribe template."""
        del parameters
        future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future
        return self.value, future


class MpfFormatter(string.Formatter):

    """String formater which replaces placeholders."""

    def __init__(self, machine, parameters, subscribe):
        """Initialise formatter."""
        self.machine = machine
        self.parameters = parameters
        self.subscriptions = []
        self.subscribe = subscribe

    def get_value(self, key, args, kwargs):
        """Return value of placeholder."""
        placeholder = self.machine.placeholder_manager.build_raw_template(key)
        if self.subscribe:
            value, future = placeholder.evaluate_and_subscribe(self.parameters)
            if future:
                self.subscriptions.append(future)
            return value
        else:
            return placeholder.evaluate(self.parameters)

    def get_field(self, field_name, args, kwargs):
        """Return value of field."""
        obj = self.get_value(field_name, args, kwargs)
        return obj, field_name

    def format_field(self, value, format_spec):
        """Format field."""
        # don't crash on None for int. the format type is always the last element in a format spec
        if value is None and format_spec[-1:] == "d":
            value = 0
        return super().format_field(value, format_spec)


class TextTemplate:

    """Text placeholder."""

    var_finder = re.compile("(?<=\\()[a-zA-Z_0-9|]+(?=\\))")
    string_finder = re.compile("(?<=\\$)[a-zA-Z_0-9]+")

    def __init__(self, machine: "MachineController", text: str) -> None:
        """Initialise placeholder."""
        self.machine = machine
        self.text = text
        self.vars = self.var_finder.findall(text)
        self._change_callback = None

    def evaluate(self, parameters) -> str:
        """Evaluate placeholder to string."""
        f = MpfFormatter(self.machine, parameters, False)
        return f.format(self.text)

    def evaluate_and_subscribe(self, parameters) -> Tuple[str, asyncio.Future]:
        """Evaluate placeholder to string and subscribe to changes."""
        f = MpfFormatter(self.machine, parameters, True)
        value = f.format(self.text)
        subscriptions = f.subscriptions
        if not subscriptions:
            future = asyncio.Future(loop=self.machine.clock.loop)   # type: asyncio.Future
        elif len(subscriptions) == 1:
            future = subscriptions[0]
        else:
            future = Util.any(subscriptions, loop=self.machine.clock.loop)
        future = Util.ensure_future(future, loop=self.machine.clock.loop)
        return value, future


class BasePlaceholder(object):

    """Base class for placeholder variables."""

    # pylint: disable-msg=no-self-use
    def subscribe(self):
        """Subscribe to placeholder."""
        raise AssertionError("Not possible to subscribe this.")

    # pylint: disable-msg=no-self-use
    def subscribe_attribute(self, item):
        """Subscribe to attribute."""
        raise AssertionError("Not possible to subscribe to attribute {}.".format(item))

    # pylint: disable-msg=no-self-use
    def subscribe_item(self, item):
        """Subscribe to item."""
        raise AssertionError("Not possible to subscribe to item {}.".format(item))


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


class PlayerPlaceholder(BasePlaceholder):

    """Wraps the player."""

    def __init__(self, machine, number=None):
        """Initialise placeholder."""
        self._machine = machine     # type: MachineController
        self._number = number

    def subscribe(self):
        """Subscribe to player changes."""
        return self._machine.events.wait_for_any_event(["player_turn_ended", "player_turn_started"])

    def subscribe_attribute(self, item):
        """Subscribe player variable changes."""
        return self._machine.events.wait_for_event('player_{}'.format(item))

    def __getitem__(self, item):
        """Array access."""
        if self._machine.game and self._machine.game.player:
            if self._number is not None:
                if len(self._machine.game.player_list) <= self._number:
                    raise ValueError("Player not in game")
                return self._machine.game.player_list[self._number][item]
            else:
                return self._machine.game.player[item]
        else:
            raise ValueError("Not in a game")

    def __getattr__(self, item):
        """Attribute access."""
        if self._machine.game and self._machine.game.player:
            if self._number is not None:
                if len(self._machine.game.player_list) <= self._number:
                    raise ValueError("Player not in game")
                return getattr(self._machine.game.player_list[self._number], item)
            else:
                return getattr(self._machine.game.player, item)
        else:
            raise ValueError("Not in a game")


class PlayersPlaceholder(BasePlaceholder):

    """Wraps the player list."""

    def __init__(self, machine):
        """Initialise placeholder."""
        self._machine = machine     # type: MachineController

    def subscribe(self):
        """Subscribe to player list changes."""
        return self._machine.events.wait_for_any_event(["player_added", "game_ended"])

    def subscribe_attribute(self, item):
        """Subscribe player variable changes."""
        return self._machine.events.wait_for_event('player_{}'.format(item))

    def __getitem__(self, item):
        """Array access."""
        return PlayerPlaceholder(self._machine, item)

    def __getattr__(self, item):
        """Attribute access."""
        return PlayerPlaceholder(self._machine, item)


class MachinePlaceholder(BasePlaceholder):

    """Wraps the machine."""

    def __init__(self, machine):
        """Initialise placeholder."""
        self._machine = machine     # type: MachineController

    def subscribe(self):
        """Subscribe to machine changes.

        Will never return.
        """
        return asyncio.Future(loop=self._machine.clock.loop)

    def subscribe_attribute(self, item):
        """Subscribe to machine variable."""
        return self._machine.events.wait_for_event('machine_var_{}'.format(item))

    def __getitem__(self, item):
        """Array access."""
        return self._machine.get_machine_var(item)

    def __getattr__(self, item):
        """Attribute access."""
        return self._machine.get_machine_var(item)


class SettingsPlaceholder(BasePlaceholder):

    """Wraps settings."""

    def __init__(self, machine):
        """Initialise placeholder."""
        self._machine = machine  # type: MachineController

    def subscribe(self):
        """Subscribe to settings controller changes.

        Will never return.
        """
        return asyncio.Future(loop=self._machine.clock.loop)

    def subscribe_attribute(self, item):
        """Subscribe to machine variable for this setting."""
        return self._machine.events.wait_for_event(
            'machine_var_{}'.format(self._machine.settings.get_setting_machine_var(item)))

    def __getattr__(self, item):
        """Attribute access."""
        return self._machine.settings.get_setting_value(item)


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

    @staticmethod
    def _eval_num(node, variables, subscribe):
        del variables
        del subscribe
        return node.n, []

    @staticmethod
    def _eval_str(node, variables, subscribe):
        del variables
        del subscribe
        return node.s, []

    @staticmethod
    def _eval_name_constant(node, variables, subscribe):
        del variables
        del subscribe
        return node.value, []

    def _eval_if(self, node, variables, subscribe):
        value, subscription = self._eval(node.test, variables, subscribe)
        if value:
            ret_value, ret_subscription = self._eval(node.body, variables, subscribe)
            return ret_value, subscription + ret_subscription
        else:
            ret_value, ret_subscription = self._eval(node.orelse, variables, subscribe)
            return ret_value, subscription + ret_subscription

    def _eval_bin_op(self, node, variables, subscribe):
        left_value, left_subscription = self._eval(node.left, variables, subscribe)
        right_value, right_subscription = self._eval(node.right, variables, subscribe)
        try:
            ret_value = operators[type(node.op)](left_value, right_value)
        except TypeError:
            raise TemplateEvalError(left_subscription + right_subscription)
        return ret_value, left_subscription + right_subscription

    def _eval_unary_op(self, node, variables, subscribe):
        value, subscription = self._eval(node.operand, variables, subscribe)
        return operators[type(node.op)](value), subscription

    def _eval_compare(self, node, variables, subscribe):
        if len(node.ops) > 1:
            raise AssertionError("Only single comparisons are supported.")
        left_value, left_subscription = self._eval(node.left, variables, subscribe)
        right_value, right_subscription = self._eval(node.comparators[0], variables, subscribe)
        try:
            return comparisons[type(node.ops[0])](left_value, right_value), left_subscription + right_subscription
        except TypeError:
            raise TemplateEvalError(left_subscription + right_subscription)

    def _eval_bool_op(self, node, variables, subscribe):
        result, subscription = self._eval(node.values[0], variables, subscribe)
        for i in range(1, len(node.values)):
            value, new_subscription = self._eval(node.values[i], variables, subscribe)
            subscription += new_subscription
            try:
                result = bool_operators[type(node.op)](result, value)
            except TypeError:
                raise TemplateEvalError(subscription)
        return result, subscription

    def _eval_attribute(self, node, variables, subscribe):
        slice_value, subscription = self._eval(node.value, variables, subscribe)
        if isinstance(slice_value, dict) and node.attr in slice_value:
            ret_value = slice_value[node.attr]
        else:
            try:
                ret_value = getattr(slice_value, node.attr)
            except ValueError:
                if subscribe:
                    raise TemplateEvalError(subscription + [slice_value.subscribe_attribute(node.attr)])
                else:
                    raise
        if subscribe:
            return ret_value, subscription + [slice_value.subscribe_attribute(node.attr)]
        else:
            return ret_value, subscription + []

    def _eval_subscript(self, node, variables, subscribe):
        value, subscription = self._eval(node.value, variables, subscribe)
        if isinstance(node.slice, ast.Index):
            slice_value, slice_subscript = self._eval(node.slice.value, variables, subscribe)
            try:
                return value[slice_value], subscription + slice_subscript
            except ValueError:
                raise TemplateEvalError(subscription + slice_subscript)
        elif isinstance(node.slice, ast.Slice):
            lower, lower_subscription = self._eval(node.slice.lower, variables, subscribe)
            upper, upper_subscription = self._eval(node.slice.upper, variables, subscribe)
            step, step_subscription = self._eval(node.slice.step, variables, subscribe)
            return value[lower:upper:step], subscription + lower_subscription + upper_subscription + step_subscription
        else:
            raise TypeError(type(node))

    def _eval_name(self, node, variables, subscribe):
        var = self.get_global_parameters(node.id)
        if var:
            if subscribe:
                return var, [var.subscribe()]
            else:
                return var, []
        elif node.id in variables:
            return variables[node.id], []
        else:
            raise ValueError("Missing variable {}".format(node.id))

    def _eval(self, node, variables, subscribe) -> Tuple[Any, List]:
        if node is None:
            return None, []

        elif type(node) in self._eval_methods:  # pylint: disable-msg=unidiomatic-typecheck
            return self._eval_methods[type(node)](node, variables, subscribe)
        else:
            raise TypeError(type(node))

    def build_float_template(self, template_str, default_value=0.0):
        """Build a float template from a string."""
        if isinstance(template_str, (float, int)):
            return NativeTypeTemplate(float(template_str), self.machine)
        return FloatTemplate(self._parse_template(template_str), self, default_value)

    def build_int_template(self, template_str, default_value=0):
        """Build a int template from a string."""
        if isinstance(template_str, (float, int)):
            return NativeTypeTemplate(int(template_str), self.machine)
        return IntTemplate(self._parse_template(template_str), self, default_value)

    def build_bool_template(self, template_str, default_value=False):
        """Build a bool template from a string."""
        if isinstance(template_str, bool):
            return NativeTypeTemplate(template_str, self.machine)
        return BoolTemplate(self._parse_template(template_str), self, default_value)

    def build_string_template(self, template_str, default_value=""):
        """Build a string template from a string."""
        return StringTemplate(self._parse_template(template_str), self, default_value)

    def build_raw_template(self, template_str, default_value=None):
        """Build a raw template from a string."""
        return RawTemplate(self._parse_template(template_str), self, default_value)

    def get_global_parameters(self, name):
        """Return global params."""
        raise NotImplementedError()

    def evaluate_template(self, template, parameters):
        """Evaluate template."""
        return self._eval(template, parameters, False)[0]

    def evaluate_and_subscribe_template(self, template, parameters):
        """Evaluate and subscribe template."""
        try:
            value, subscriptions = self._eval(template, parameters, True)
        except TemplateEvalError as e:
            value = e
            subscriptions = e.subscriptions

        if not subscriptions:
            future = asyncio.Future(loop=self.machine.clock.loop)
        elif len(subscriptions) == 1:
            future = subscriptions[0]
        else:
            future = Util.any(subscriptions, loop=self.machine.clock.loop)
        future = Util.ensure_future(future, loop=self.machine.clock.loop)
        return value, future

    def parse_conditional_template(self, template, default_number=None):
        """Parse a template for condition and number and return a dict."""
        # The following regex will make a dict for event name, condition, and number
        # e.g. some_event_name_string{variable.condition==True}|num
        #      ^ string at start     ^ condition in braces     ^ pipe- or colon-delimited value
        match = re.search(r"^(?P<name>[^{}:\|]*)(\{(?P<condition>.+)\})?([|:](?P<number>.+))?$", template)
        if not match:
            raise AssertionError("Invalid template string {}".format(template))

        match_dict = match.groupdict()

        # Create a Template object for the condition
        if match_dict['condition'] is not None:
            match_dict['condition'] = self.build_bool_template(match_dict['condition'])

        if default_number is not None:
            # Fill in the default number if the template has none
            if match_dict['number'] is None:
                match_dict['number'] = default_number
            else:
                # Type-conform the template number to the default_number type
                try:
                    match_dict['number'] = type(default_number)(match_dict['number'])
                # Gracefully fall back if the number can't be parsed
                except ValueError:
                    self.warning_log("Condition '{}' has invalid number value '{}'".format(
                                     template, match_dict['number']))
                    match_dict['number'] = default_number
        return match_dict


class PlaceholderManager(BasePlaceholderManager):

    """Manages templates and placeholders for MPF."""

    # pylint: disable-msg=too-many-return-statements
    def get_global_parameters(self, name):
        """Return global params."""
        if name == "settings":
            return SettingsPlaceholder(self.machine)
        elif name == "machine":
            return MachinePlaceholder(self.machine)
        elif name == "device":
            return DevicesPlaceholder(self.machine)
        elif name == "mode":
            return ModePlaceholder(self.machine)
        elif name == "current_player":
            return PlayerPlaceholder(self.machine)
        elif name == "players":
            return PlayersPlaceholder(self.machine)
        elif self.machine.game:
            if name == "game":
                return self.machine.game

        return False
