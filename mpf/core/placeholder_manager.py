"""Templates and placeholders."""
import sympy

from mpf.core.mpf_controller import MpfController


class PlaceholderManager(MpfController):

    """Manages templates and placeholders for MPF."""

    def build_bool_template(self, template_str):
        """Build a template from a string."""
        return sympy.sympify(template_str)

    def evaluate_bool_template(self, template, parameters, fail_on_missing_params=False):
        """Return True if the placeholder"""
        # replace parameters
        result = template.subs(parameters)
        if fail_on_missing_params and result.free_symbols:
            raise AssertionError("Free symbols {} in condition".format(result.free_symbols))

        return result == True