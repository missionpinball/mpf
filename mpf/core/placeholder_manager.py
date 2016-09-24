"""Templates and placeholders."""
import ast
import operator as op
from mpf.core.mpf_controller import MpfController

# supported operators
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg, ast.Not: op.not_}

bool_operators = {ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b}

comparisons = {ast.Eq: op.eq, ast.Lt: op.lt, ast.Gt: op.gt, ast.LtE: op.le, ast.GtE: op.ge}


class PlaceholderManager(MpfController):

    """Manages templates and placeholders for MPF."""

    def _parse_template(selfc, template_str):
        return ast.parse(template_str, mode='eval').body

    def _eval_template(self, template, variables):
        """Evaluate a template."""
        return self._eval(template, variables)

    def _eval(self, node, variables):
        if isinstance(node, ast.Num):   # <number>
            return node.n
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
            if node.value.id == "settings":
                return self.machine.settings.get_setting_value(node.attr)
            else:
                raise AssertionError("Invalid attribute")
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            else:
                raise ValueError("Mising variable {}".format(node.id))
        else:
            raise TypeError(node)

    def build_bool_template(self, template_str):
        """Build a template from a string."""
        template = self._parse_template(template_str)
        return template

    def evaluate_bool_template(self, template, parameters, fail_on_missing_params=False):
        """Return True if the placeholder"""
        # replace parameters
        try:
            result = self._eval_template(template, parameters)
        except ValueError:
            if fail_on_missing_params:
                raise
            return False
        return result == True