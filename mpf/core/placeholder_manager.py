"""Templates and placeholders."""
import ast
import operator as op
import abc

from mpf.core.mpf_controller import MpfController

# supported operators
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg, ast.Not: op.not_}

bool_operators = {ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b}

comparisons = {ast.Eq: op.eq, ast.Lt: op.lt, ast.Gt: op.gt, ast.LtE: op.le, ast.GtE: op.ge}


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


class PlaceholderManager(MpfController):

    """Manages templates and placeholders for MPF."""

    @staticmethod
    def _parse_template(template_str):
        return ast.parse(template_str, mode='eval').body

    def _eval_subscript(self, node, variables):
        if isinstance(node.slice, ast.Index):
            return self._eval(node.value, variables)[self._eval(node.slice.value, variables)]
        elif isinstance(node.slice, ast.Slice):
            return self._eval(node.value, variables)[self._eval(node.slice.lower, variables):
                                                     self._eval(node.slice.upper, variables):
                                                     self._eval(node.slice.step, variables)]
        else:
            raise TypeError(type(node))

    def _eval(self, node, variables):
        if isinstance(node, ast.Num):   # <number>
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        elif node is None:
            return None
        elif isinstance(node, ast.NameConstant):   # <number>
            return node.value
        elif isinstance(node, ast.BinOp):       # <left> <operator> <right>
            return operators[type(node.op)](self._eval(node.left, variables), self._eval(node.right, variables))
        elif isinstance(node, ast.UnaryOp):     # <operator> <operand> e.g., -1
            return operators[type(node.op)](self._eval(node.operand, variables))
        elif isinstance(node, ast.Compare):
            if len(node.ops) > 1:
                raise AssertionError("Only single comparisons are supported.")
            return comparisons[type(node.ops[0])](self._eval(node.left, variables),
                                                  self._eval(node.comparators[0], variables))
        elif isinstance(node, ast.BoolOp):
            result = self._eval(node.values[0], variables)
            for i in range(1, len(node.values)):
                result = bool_operators[type(node.op)](result,
                                                       self._eval(node.values[i], variables))
            return result
        elif isinstance(node, ast.Attribute):
            return getattr(self._eval(node.value, variables), node.attr)
        elif isinstance(node, ast.Subscript):
            return self._eval_subscript(node, variables)
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            else:
                raise ValueError("Mising variable {}".format(node.id))
        else:
            raise TypeError(type(node))

    def build_float_template(self, template_str, default_value=0.0):
        """Build a float template from a string."""
        return FloatTemplate(self._parse_template(template_str), self, default_value)

    def build_int_template(self, template_str, default_value=0):
        """Build a int template from a string."""
        return IntTemplate(self._parse_template(template_str), self, default_value)

    def build_bool_template(self, template_str, default_value=False):
        """Build a bool template from a string."""
        return BoolTemplate(self._parse_template(template_str), self, default_value)

    def evaluate_template(self, template, parameters):
        """Evaluate template."""
        parameters["settings"] = self.machine.settings
        if self.machine.game:
            parameters["current_player"] = self.machine.game.player
            parameters["players"] = self.machine.game.player_list
            parameters["game"] = self.machine.game
        return self._eval(template, parameters)
