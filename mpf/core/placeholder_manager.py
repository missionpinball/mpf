"""Templates and placeholders."""
import ast
import string
import asyncio
import operator as op
import abc
from functools import lru_cache

import re
from typing import Tuple, List, Any, Union

from mpf.core.utility_functions import Util

from mpf.core.mpf_controller import MpfController
from mpf.exceptions.config_file_error import ConfigFileError

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


# supported operators
OPERATORS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.FloorDiv: op.floordiv,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg, ast.Not: op.not_, ast.Mod: op.mod}

BOOL_OPERATORS = {ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b}

COMPARISONS = {ast.Eq: op.eq, ast.Lt: op.lt, ast.Gt: op.gt, ast.LtE: op.le, ast.GtE: op.ge, ast.NotEq: op.ne}


class ConditionalEvent:

    """An conditional event."""

    __slots__ = ["name", "condition", "number"]

    def __init__(self, name, condition, number):
        """initialize conditional event."""
        self.name = name
        self.condition = condition
        self.number = number

    def __repr__(self):
        """Return string representation."""
        return "{}-{}-{}".format(self.name, self.condition, self.number)


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

    __slots__ = ["template", "placeholder_manager", "default_value", "text"]

    def __init__(self, template, text, placeholder_manger, default_value):
        """initialize template."""
        self.text = str(text)
        self.template = template
        self.placeholder_manager = placeholder_manger
        self.default_value = default_value

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Evaluate template and convert the result."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except ValueError:
            if fail_on_missing_params:
                raise
            return self.default_value
        except TemplateEvalError:
            return self.default_value
        except ConfigFileError:     # pylint: disable-msg=try-except-raise
            raise
        except Exception as e:
            raise AssertionError("Failed to evaluate {} template {} with parameters {}".format(
                type(self), self.text, parameters)) from e

        if result is None:
            return self.default_value
        return self.convert_result(result)

    def evaluate_or_none(self, parameters):
        """Evaluate template and convert the result or return None."""
        try:
            result = self.placeholder_manager.evaluate_template(self.template, parameters)
        except ValueError:
            return None
        if result is None:
            return None
        return self.convert_result(result)

    def evaluate_and_subscribe(self, parameters) -> Tuple[bool, asyncio.Future]:
        """Evaluate template and subscribe."""
        result, subscriptions = self.placeholder_manager.evaluate_and_subscribe_template(self.template, parameters,
                                                                                         self.text)
        if isinstance(result, TemplateEvalError) or result is None:
            result = self.default_value
        return self.convert_result(result), subscriptions

    @abc.abstractmethod
    def convert_result(self, value):
        """Convert the result of the template."""

    def __repr__(self):
        """Return string representation."""
        return "<Template {}>".format(self.text)


class BoolTemplate(BaseTemplate):

    """Bool template."""

    __slots__ = []  # type: List[str]

    def convert_result(self, value):
        """Convert the result to bool."""
        return bool(value)


class FloatTemplate(BaseTemplate):

    """Float template."""

    __slots__ = []  # type: List[str]

    def convert_result(self, value):
        """Convert the result to float."""
        return float(value)


class IntTemplate(BaseTemplate):

    """Float template."""

    __slots__ = []  # type: List[str]

    def convert_result(self, value):
        """Convert the result to int."""
        return int(value)


class StringTemplate(BaseTemplate):

    """String template."""

    __slots__ = []  # type: List[str]

    def convert_result(self, value):
        """Convert the result to str."""
        return str(value)


class RawTemplate(BaseTemplate):

    """Raw template."""

    __slots__ = []  # type: List[str]

    def convert_result(self, value):
        """Keep the value."""
        return value


class NativeTypeTemplate:

    """Native type template which encapsulates an int/float/bool."""

    __slots__ = ["value", "machine"]

    def __init__(self, value, machine):
        """Set value."""
        self.value = value
        self.machine = machine

    def evaluate(self, parameters, fail_on_missing_params=False):
        """Return value."""
        del parameters
        del fail_on_missing_params
        return self.value

    def evaluate_or_none(self, parameters):
        """Return value."""
        del parameters
        return self.value

    def evaluate_and_subscribe(self, parameters) -> Tuple[int, asyncio.Future]:
        """Evaluate and subscribe template."""
        del parameters
        future = asyncio.Future()   # type: asyncio.Future
        return self.value, future

    def __eq__(self, other):
        """Templates are equal if values are equal."""
        return other.value == self.value

    def __repr__(self):
        """Return String."""
        return "<NativeTemplate {}>".format(self.value)


class MpfFormatter(string.Formatter):

    """String formater which replaces placeholders."""

    __slots__ = ["machine", "parameters", "subscriptions", "subscribe"]

    def __init__(self, machine, parameters, subscribe):
        """initialize formatter."""
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
        try:
            return super().format_field(value, format_spec)
        except Exception as e:
            raise AssertionError("Could not format {} with {}".format(format_spec, value)) from e


class TextTemplate:

    """Text placeholder."""

    __slots__ = ["machine", "text", "_change_callback"]

    def __init__(self, machine: "MachineController", text: str) -> None:
        """initialize placeholder."""
        self.machine = machine
        self.text = str(text)
        self._change_callback = None

    def evaluate(self, parameters) -> str:
        """Evaluate placeholder to string."""
        try:
            f = MpfFormatter(self.machine, parameters, False)
            return f.format(self.text)
        except Exception as e:
            raise AssertionError("Failed to format {} with {}".format(self.text, parameters)) from e

    def evaluate_and_subscribe(self, parameters) -> Tuple[str, asyncio.Future]:
        """Evaluate placeholder to string and subscribe to changes."""
        f = MpfFormatter(self.machine, parameters, True)
        value = f.format(self.text)
        subscriptions = f.subscriptions
        if not subscriptions:
            future = asyncio.Future()   # type: asyncio.Future
        elif len(subscriptions) == 1:
            future = subscriptions[0]
        else:
            future = Util.any(subscriptions)
        future = asyncio.ensure_future(future)
        return value, future


class BasePlaceholder:

    """Base class for placeholder variables."""

    __slots__ = []  # type: List[str]

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


class DevicePlaceholder:

    """Wrap a monitorable device."""

    __slots__ = ["_device", "_attribute", "_machine"]

    def __init__(self, device, attribute, machine):
        """initialize placeholder."""
        self._device = device
        self._attribute = attribute
        self._machine = machine

    @staticmethod
    def subscribe():
        """Subscribe to object changes."""
        return asyncio.Future()

    def subscribe_attribute(self, item):
        """Subscribe to device changes."""
        return self._device.subscribe_attribute(item, self._machine)

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    def __getattr__(self, item):
        """Attribute access."""
        return self._device.get_placeholder_value(item)


class DeviceClassPlaceholder:

    """Wrap a monitorable device class."""

    __slots__ = ["_devices", "_device_name", "_machine"]

    def __init__(self, devices, device_name, machine):
        """initialize placeholder."""
        self._devices = devices
        self._device_name = device_name
        self._machine = machine

    @staticmethod
    def subscribe():
        """Subscribe to object changes."""
        return asyncio.Future()

    @staticmethod
    def subscribe_attribute(item):
        """Subscribe to device changes."""
        del item
        return asyncio.Future()

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    def __getattr__(self, item):
        """Attribute access."""
        device = self._devices.get(item)
        if not device:
            raise AssertionError("Device {} of type {} does not exist.".format(item, self._device_name))

        return DevicePlaceholder(device, item, self._machine)


class DevicesPlaceholder:

    """Device monitor placeholder."""

    __slots__ = ["_machine"]

    def __init__(self, machine):
        """initialize placeholder."""
        self._machine = machine

    def __getitem__(self, item):
        """Array access."""
        return self.__getattr__(item)

    @staticmethod
    def subscribe():
        """Subscribe to object changes."""
        return asyncio.Future()

    @staticmethod
    def subscribe_attribute(item):
        """Subscribe to device changes."""
        del item
        return asyncio.Future()

    def __getattr__(self, item):
        """Attribute access."""
        device = self._machine.device_manager.get_monitorable_devices().get(item)
        if not device:
            raise AssertionError("Device Collection {} not usable in placeholders.".format(item))
        return DeviceClassPlaceholder(device, item, self._machine)


class ModeClassPlaceholder:

    """Wrap a mode."""

    __slots__ = ["_mode"]

    def __init__(self, mode):
        """initialize placeholder."""
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

    __slots__ = ["_machine"]

    def __init__(self, machine):
        """initialize placeholder."""
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

    __slots__ = ["_machine", "_number"]

    def __init__(self, machine, number=None):
        """initialize placeholder."""
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

            return self._machine.game.player[item]

        raise ValueError("Not in a game")

    def __getattr__(self, item):
        """Attribute access."""
        if self._machine.game and self._machine.game.player:
            if self._number is not None:
                if len(self._machine.game.player_list) <= self._number:
                    raise ValueError("Player not in game")
                return getattr(self._machine.game.player_list[self._number], item)

            return getattr(self._machine.game.player, item)

        raise ValueError("Not in a game")


class PlayersPlaceholder(BasePlaceholder):

    """Wraps the player list."""

    __slots__ = ["_machine"]

    def __init__(self, machine):
        """initialize placeholder."""
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


class TimePlaceholder(BasePlaceholder):

    """Return current time."""

    __slots__ = ["_machine"]

    def __init__(self, machine):
        """initialize placeholder."""
        self._machine = machine     # type: MachineController

    def subscribe(self):
        """Subscribe to machine changes.

        Will never return.
        """
        return asyncio.Future()

    def subscribe_attribute(self, item):
        """Invalidate time placeholders when they are due."""
        current_time = self._machine.clock.get_datetime()
        if item == "second":
            return asyncio.sleep(1)
        if item == "minute":
            return asyncio.sleep(60 - current_time.second)
        if item in ("hour", "day", "month", "year"):
            # we will reevaluate day, month and year every hour
            return asyncio.sleep(3600 - current_time.second - 60 * current_time.minute)

        raise AssertionError("Invalid time element {}".format(item))

    def __getattr__(self, item):
        """Attribute access."""
        current_time = self._machine.clock.get_datetime()
        if item == "second":
            return current_time.second
        if item == "minute":
            return current_time.minute
        if item == "hour":
            return current_time.hour
        if item == "day":
            return current_time.day
        if item == "month":
            return current_time.month
        if item == "year":
            return current_time.year

        raise AssertionError("Invalid time element {}".format(item))


class MachinePlaceholder(BasePlaceholder):

    """Wraps the machine."""

    __slots__ = ["_machine"]

    def __init__(self, machine):
        """initialize placeholder."""
        self._machine = machine     # type: MachineController

    def subscribe(self):
        """Subscribe to machine changes.

        Will never return.
        """
        return asyncio.Future()

    def subscribe_attribute(self, item):
        """Subscribe to machine variable."""
        if item == "time":
            return asyncio.Future()
        return self._machine.events.wait_for_event('machine_var_{}'.format(item))

    def __getitem__(self, item):
        """Array access."""
        return self._machine.variables.get_machine_var(item)

    def __getattr__(self, item):
        """Attribute access."""
        if item == "time":
            return TimePlaceholder(self._machine)
        return self._machine.variables.get_machine_var(item)


class SettingsPlaceholder(BasePlaceholder):

    """Wraps settings."""

    __slots__ = ["_machine"]

    def __init__(self, machine):
        """initialize placeholder."""
        self._machine = machine  # type: MachineController

    def subscribe(self):
        """Subscribe to settings controller changes.

        Will never return.
        """
        return asyncio.Future()

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

    __slots__ = ["_eval_methods"]

    def __init__(self, machine):
        """initialize."""
        super().__init__(machine)
        self._eval_methods = {
            ast.Num: self._eval_num,
            ast.Str: self._eval_str,
            ast.NameConstant: self._eval_constant,
            ast.BinOp: self._eval_bin_op,
            ast.UnaryOp: self._eval_unary_op,
            ast.Compare: self._eval_compare,
            ast.BoolOp: self._eval_bool_op,
            ast.Attribute: self._eval_attribute,
            ast.Subscript: self._eval_subscript,
            ast.Name: self._eval_name,
            ast.IfExp: self._eval_if,
            ast.Tuple: self._eval_tuple,
        }
        if hasattr(ast, "Constant"):
            self._eval_methods[ast.Constant] = self._eval_constant

    def _eval_tuple(self, node, variables, subscribe):
        return tuple([self._eval(x, variables, subscribe) for x in node.elts])

    @staticmethod
    def _parse_template(template_str):
        try:
            return ast.parse(template_str, mode='eval').body
        except SyntaxError:
            raise AssertionError('Failed to parse template "{}"'.format(template_str))

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
    def _eval_constant(node, variables, subscribe):
        del variables
        del subscribe
        return node.value, []

    def _eval_if(self, node, variables, subscribe):
        value, subscription = self._eval(node.test, variables, subscribe)
        if value:
            ret_value, ret_subscription = self._eval(node.body, variables, subscribe)
            return ret_value, subscription + ret_subscription

        ret_value, ret_subscription = self._eval(node.orelse, variables, subscribe)
        return ret_value, subscription + ret_subscription

    def _eval_bin_op(self, node, variables, subscribe):
        left_value, left_subscription = self._eval(node.left, variables, subscribe)
        right_value, right_subscription = self._eval(node.right, variables, subscribe)
        try:
            ret_value = OPERATORS[type(node.op)](left_value, right_value)
        except TypeError:
            raise TemplateEvalError(left_subscription + right_subscription)
        return ret_value, left_subscription + right_subscription

    def _eval_unary_op(self, node, variables, subscribe):
        value, subscription = self._eval(node.operand, variables, subscribe)
        return OPERATORS[type(node.op)](value), subscription

    def _eval_compare(self, node, variables, subscribe):
        if len(node.ops) > 1:
            raise AssertionError("Only single comparisons are supported.")
        left_value, left_subscription = self._eval(node.left, variables, subscribe)
        right_value, right_subscription = self._eval(node.comparators[0], variables, subscribe)
        try:
            return COMPARISONS[type(node.ops[0])](left_value, right_value), left_subscription + right_subscription
        except TypeError:
            raise TemplateEvalError(left_subscription + right_subscription)

    def _eval_bool_op(self, node, variables, subscribe):
        result, subscription = self._eval(node.values[0], variables, subscribe)
        for i in range(1, len(node.values)):
            value, new_subscription = self._eval(node.values[i], variables, subscribe)
            subscription += new_subscription
            try:
                result = BOOL_OPERATORS[type(node.op)](result, value)
            except TypeError:
                raise TemplateEvalError(subscription)
        return result, subscription

    def _eval_attribute(self, node, variables, subscribe):
        slice_value, subscription = self._eval(node.value, variables, subscribe)
        if slice_value is None or not slice_value:
            if subscribe:  # pylint: disable-msg=no-else-raise
                raise TemplateEvalError(subscription)
            else:
                raise AssertionError("Cannot access {} in path because the parent is None".format(node))
        if isinstance(slice_value, dict) and node.attr in slice_value:
            ret_value = slice_value[node.attr]
        else:
            try:
                ret_value = getattr(slice_value, node.attr)
            except (ValueError, AttributeError):
                if subscribe:   # pylint: disable-msg=no-else-raise
                    raise TemplateEvalError(subscription + [slice_value.subscribe_attribute(node.attr)])
                else:
                    raise
        if subscribe:
            return ret_value, subscription + [slice_value.subscribe_attribute(node.attr)]

        return ret_value, subscription + []

    def _eval_subscript(self, node, variables, subscribe):
        value, subscription = self._eval(node.value, variables, subscribe)
        if isinstance(node.slice, ast.Constant):
            return value[node.slice.value], subscription
        if isinstance(node.slice, ast.Index):
            slice_value, slice_subscript = self._eval(node.slice.value, variables, subscribe)
            try:
                return value[slice_value], subscription + slice_subscript
            except ValueError:
                raise TemplateEvalError(subscription + slice_subscript)
        if isinstance(node.slice, ast.Slice):
            lower, lower_subscription = self._eval(node.slice.lower, variables, subscribe)
            upper, upper_subscription = self._eval(node.slice.upper, variables, subscribe)
            step, step_subscription = self._eval(node.slice.step, variables, subscribe)
            return value[lower:upper:step], subscription + lower_subscription + upper_subscription + step_subscription

        raise TypeError(type(node.slice))

    def _eval_name(self, node, variables, subscribe):
        if node.id in ("true", "false"):
            self.raise_config_error("Placeholder use Python syntax. Use True "
                                    "and False instead of true and false.", 1,
                                    context=node.id)

        var = self.get_global_parameters(node.id)
        if var:
            if subscribe:
                return var, [var.subscribe()]

            return var, []
        if node.id in variables:
            return variables[node.id], []

        raise ValueError("Missing variable {}".format(node.id))

    def _eval(self, node, variables, subscribe) -> Tuple[Any, List]:
        if node is None:
            return None, []

        if type(node) in self._eval_methods:  # pylint: disable-msg=unidiomatic-typecheck
            return self._eval_methods[type(node)](node, variables, subscribe)

        raise TypeError(type(node))

    def build_float_template(self, template_str, default_value=0.0) -> Union[FloatTemplate, NativeTypeTemplate]:
        """Build a float template from a string."""
        # try to convert to int
        try:
            value = float(template_str)
        except ValueError:
            pass
        else:
            return NativeTypeTemplate(value, self.machine)  # type: ignore

        return FloatTemplate(self._parse_template(template_str), template_str, self, default_value)

    def build_int_template(self, template_str, default_value=0) -> Union[IntTemplate, NativeTypeTemplate]:
        """Build a int template from a string."""
        # try to convert to int
        try:
            value = int(template_str)
        except ValueError:
            pass
        else:
            return NativeTypeTemplate(value, self.machine)  # type: ignore

        return IntTemplate(self._parse_template(template_str), template_str, self, default_value)

    def build_bool_template(self, template_str, default_value=False) -> Union[BoolTemplate, NativeTypeTemplate]:
        """Build a bool template from a string."""
        if isinstance(template_str, bool):
            return NativeTypeTemplate(template_str, self.machine)   # type: ignore
        return BoolTemplate(self._parse_template(template_str), template_str, self, default_value)

    def build_string_template(self, template_str, default_value=""):
        """Build a string template from a string."""
        return StringTemplate(self._parse_template(template_str), template_str, self, default_value)

    def build_text_template(self, template_str):
        """Build a full featured text template."""
        return TextTemplate(self.machine, template_str)

    def build_quoted_string_template(self, template_str, default_value=""):
        """Build a string template from a string if enclosed in brackets."""
        if isinstance(template_str, str) and (template_str[0:1] != "(" or template_str[-1:] != ")"):
            return NativeTypeTemplate(template_str, self.machine)
        return StringTemplate(self._parse_template(template_str), template_str, self, default_value)

    def build_raw_template(self, template_str, default_value=None) -> RawTemplate:
        """Build a raw template from a string."""
        return RawTemplate(self._parse_template(template_str), template_str, self, default_value)

    def get_global_parameters(self, name):
        """Return global params."""
        raise NotImplementedError()

    def evaluate_template(self, template, parameters):
        """Evaluate template."""
        return self._eval(template, parameters, False)[0]

    def evaluate_and_subscribe_template(self, template, parameters, text=None):
        """Evaluate and subscribe template."""
        if self.machine.stop_future.done():
            # return a canceled future if machine is already stopping
            future = asyncio.Future()
            future.cancel()
            return None, future

        try:
            value, subscriptions = self._eval(template, parameters, True)
        except TemplateEvalError as e:
            value = e
            subscriptions = e.subscriptions
        except ConfigFileError:     # pylint: disable-msg=try-except-raise
            raise
        except ValueError as e:
            raise AssertionError("Failed to evaluate and subscribe template {} with parameters {}. "
                                 "See error above.".format(text, parameters)) from e

        if not subscriptions:
            future = self.machine.wait_for_stop()
        else:
            subscriptions.append(self.machine.wait_for_stop())
            future = Util.any(subscriptions)
        future = asyncio.ensure_future(future)
        return value, future

    @lru_cache(typed=True)
    def parse_conditional_template(self, template, default_number=None):
        """Parse a template for condition and number and return a dict."""
        # The following regex will make a dict for event name, condition, and number
        # e.g. some_event_name_string{variable.condition==True}|num
        #      ^ string at start     ^ condition in braces     ^ pipe- or colon-delimited value
        match = re.search(r"^(?P<name>[^{}:| ]+)({(?P<condition>.+)})?([|:](?P<number>.+))?$", template)
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
        return ConditionalEvent(match_dict["name"], match_dict["condition"], match_dict["number"])


class PlaceholderManager(BasePlaceholderManager):

    """Manages templates and placeholders for MPF."""

    __slots__ = []  # type: List[str]

    # pylint: disable-msg=too-many-return-statements
    def get_global_parameters(self, name):
        """Return global params."""
        if name == "settings":
            return SettingsPlaceholder(self.machine)
        if name == "machine":
            return MachinePlaceholder(self.machine)
        if name == "device":
            return DevicesPlaceholder(self.machine)
        if name == "mode":
            return ModePlaceholder(self.machine)
        if name == "current_player":
            return PlayerPlaceholder(self.machine)
        if name == "players":
            return PlayersPlaceholder(self.machine)
        if name == "game" and self.machine.game:
            return self.machine.game

        return False
