"""Config specs and validator."""
import logging
import os
import re
import tempfile
from collections import OrderedDict
from copy import deepcopy

import pickle   # nosec

from typing import Any
from typing import Dict

from pkg_resources import iter_entry_points

import mpf
from mpf.core.rgb_color import NAMED_RGB_COLORS, RGBColor
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.core.utility_functions import Util

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class RuntimeToken:

    """A runtime token."""

    def __init__(self, token, validator_function):
        """Create a runtime token."""
        self.token = token
        self.validator_function = validator_function

    def __repr__(self):
        """Return string representation."""
        return "<RuntimeToken ({})>".format(self.token)


class ConfigValidator:

    """Validates config against config specs."""

    class_cache = None

    __slots__ = ["machine", "config_spec", "log", "_load_cache", "_store_cache", "validator_list"]

    def __init__(self, machine, load_cache, store_cache):
        """Initialise validator."""
        self.machine = machine      # type: MachineController
        self.config_spec = None     # type: Any
        self.log = logging.getLogger('ConfigValidator')
        self._load_cache = load_cache
        self._store_cache = store_cache

        self.validator_list = {
            "str": self._validate_type_str,
            "lstr": self._validate_type_lstr,
            "float": self._validate_type_float,
            "float_or_token": self._validate_type_or_token(self._validate_type_float),
            "int": self._validate_type_int,
            "int_or_token": self._validate_type_or_token(self._validate_type_int),
            "num": self._validate_type_num,
            "num_or_token": self._validate_type_or_token(self._validate_type_num),
            "bool": self._validate_type_bool,
            "bool_or_token": self._validate_type_or_token(self._validate_type_bool),
            "template_float": self._validate_type_template_float,
            "template_int": self._validate_type_template_int,
            "template_bool": self._validate_type_template_bool,
            "template_secs": self._validate_type_template_secs,
            "template_ms": self._validate_type_template_ms,
            "template_str": self._validate_type_template_str,
            "boolean": self._validate_type_bool,
            "ms": self._validate_type_ms,
            "ms_or_token": self._validate_type_or_token(self._validate_type_ms),
            "secs": self._validate_type_secs,
            "secs_or_token": self._validate_type_or_token(self._validate_type_secs),
            "list": self._validate_type_list,
            "int_from_hex": self._validate_type_int_from_hex,
            "dict": self._validate_type_dict,
            "omap": self._validate_type_omap,
            "kivycolor": self._validate_type_kivycolor,
            "color": self._validate_type_color,
            "bool_int": self._validate_type_bool_int,
            "pow2": self._validate_type_pow2,
            "gain": self._validate_type_gain,
            "subconfig": self._validate_type_subconfig,
            "enum": self._validate_type_enum,
            "machine": self._validate_type_machine,
        }

    @staticmethod
    def _validate_type_or_token(func):
        def _validate_type_or_token_real(item, validation_failure_info, param=None):
            if isinstance(item, str) and item.startswith("(") and item.endswith(")"):
                return RuntimeToken(item[1:-1], func)
            return func(item, validation_failure_info, param)
        return _validate_type_or_token_real

    def load_device_config_spec(self, config_section, config_spec):
        """Load config specs for a device."""
        self.config_spec[config_section] = self._process_config_spec(YamlInterface.process(config_spec), config_section)

    def load_mode_config_spec(self, mode_string, config_spec):
        """Load config specs for a mode."""
        if '_mode_settings' not in self.config_spec:
            self.config_spec['_mode_settings'] = {}
        if mode_string not in self.config_spec['_mode_settings']:
            config = YamlInterface.process(config_spec)
            self.config_spec['_mode_settings'][mode_string] = self._process_config_spec(config, mode_string)

    @staticmethod
    def get_cache_dir():
        """Return cache dir."""
        return tempfile.gettempdir()

    def load_config_spec(self):
        """Load config spec."""
        if ConfigValidator.class_cache:
            self.config_spec = ConfigValidator.class_cache
            return

        cache_file = os.path.join(self.get_cache_dir(), "config_spec.mpf_cache")
        config_spec_file = os.path.abspath(os.path.join(mpf.core.__path__[0], os.pardir, "config_spec.yaml"))
        stats_config_spec_file = os.stat(config_spec_file)
        if self._load_cache and os.path.isfile(cache_file) and \
                os.path.getmtime(cache_file) == stats_config_spec_file.st_mtime:
            try:
                with open(cache_file, 'rb') as f:
                    self.config_spec = pickle.load(f)   # nosec
                    ConfigValidator.class_cache = deepcopy(self.config_spec)
                    return
            except Exception:   # noqa
                pass

        with open(config_spec_file, 'rb') as f:
            config_str = f.read()

        config = YamlInterface.process(config_str)
        config = self._process_config_spec(config, "root")

        self.config_spec = config
        self.load_external_platform_config_specs()

        if self._store_cache:
            with open(cache_file, 'wb') as f:
                pickle.dump(config, f, protocol=4)
                os.utime(cache_file, ns=(stats_config_spec_file.st_atime_ns, stats_config_spec_file.st_mtime_ns))
                self.log.info('Config spec file cache created: %s', cache_file)

        ConfigValidator.class_cache = deepcopy(self.config_spec)

    def load_external_platform_config_specs(self):
        """Load config spec for external platforms."""
        for platform_entry in iter_entry_points(group='mpf.platforms'):
            config_spec = platform_entry.load().get_config_spec()

            if config_spec:
                # add specific config spec if platform has any
                self.load_device_config_spec(config_spec[0], config_spec[1])

    def _process_config_spec(self, spec, path):
        if not isinstance(spec, dict):
            raise AssertionError("Expected a dict at: {} {}".format(path, spec))

        for element, value in spec.items():
            if element.startswith("__"):
                spec[element] = value
            elif isinstance(value, str):
                if value == "ignore":
                    spec[element] = value
                else:
                    spec[element] = value.split('|')
                    if len(spec[element]) != 3:
                        raise AssertionError("Format incorrect: {}".format(value))
            else:
                spec[element] = self._process_config_spec(value, path + ":" + element)

        return spec

    def get_config_spec(self):
        """Return config spec."""
        if not self.config_spec:
            self.load_config_spec()

        return self.config_spec

    def unload_config_spec(self):
        """Unload specs."""
        self.config_spec = None

    def build_spec(self, config_spec, base_spec):
        """Build config spec out of two or more specs."""
        if not self.config_spec:
            self.load_config_spec()

        # build up the actual config spec we're going to use
        spec_list = [config_spec]

        if base_spec:
            if isinstance(base_spec, list):
                spec_list.extend(base_spec)
            else:
                spec_list.append(base_spec)

        this_spec = dict()
        for spec_element in spec_list:
            this_base_spec = self.config_spec
            spec_element = spec_element.split(':')
            for spec in spec_element:
                # need to deepcopy so the orig base spec doesn't get polluted
                # with this widget's spec
                this_base_spec = deepcopy(this_base_spec[spec])

            this_base_spec.update(this_spec)
            this_spec = this_base_spec

        return this_spec

    # pylint: disable-msg=too-many-arguments,too-many-branches
    def validate_config(self, config_spec, source, section_name=None,
                        base_spec=None, add_missing_keys=True, prefix=None) -> Dict[str, Any]:
        """Validate a config dict against spec."""
        # config_spec, str i.e. "device:shot"
        # source is dict
        # section_name is str used for logging failures

        if not self.config_spec:
            self.load_config_spec()

        if source is None:
            source = dict()

        if not section_name:
            section_name = config_spec  # str

        if prefix:
            validation_failure_info = (prefix + ":" + config_spec, section_name)
        else:
            validation_failure_info = (config_spec, section_name)

        this_spec = self.build_spec(config_spec, base_spec)

        if '__allow_others__' not in this_spec:
            self.check_for_invalid_sections(this_spec, source,
                                            validation_failure_info)

        processed_config = source

        if not isinstance(source, (list, dict)):
            self.validation_error("", validation_failure_info, "Source should be list or dict but is {}".format(
                source.__class__
            ))

        for k in list(this_spec.keys()):
            if this_spec[k] == 'ignore' or k[0] == '_':
                continue

            elif k in source:  # validate the entry that exists

                if isinstance(this_spec[k], dict):
                    # This means we're looking for a list of dicts

                    final_list = list()
                    if k in source:
                        for i in source[k]:  # individual step
                            final_list.append(self.validate_config(
                                config_spec + ':' + k, source=i,
                                section_name=k))

                    processed_config[k] = final_list

                else:
                    processed_config[k] = self.validate_config_item(
                        this_spec[k], item=source[k],
                        validation_failure_info=(validation_failure_info, k))

            elif add_missing_keys:  # create the default entry

                if isinstance(this_spec[k], dict):
                    processed_config[k] = list()

                else:
                    processed_config[k] = self.validate_config_item(
                        this_spec[k],
                        validation_failure_info=(
                            validation_failure_info, k))

        return processed_config

    def validate_config_item(self, spec, validation_failure_info,
                             item='item not in config!@#', ):
        """Validate a config item."""
        try:
            item_type, validation, default = spec
        except (ValueError, AttributeError):
            raise ValueError('Error in validator spec: {}:{}'.format(
                validation_failure_info, spec))

        if default.lower() == 'none':
            default = None
        elif not default:
            default = 'default required!@#'

        if item == 'item not in config!@#':
            if default == 'default required!@#':
                self.validation_error("None", validation_failure_info,
                                      'Required setting {} missing from config file.'.format(
                                          validation_failure_info[1]), 9)
            else:
                item = default

        if item_type == 'single':
            return self.validate_item(item, validation,
                                      validation_failure_info)

        if item_type == 'list':
            item_list = Util.string_to_list(item)

            new_list = list()

            for i in item_list:
                new_list.append(self.validate_item(i, validation, validation_failure_info))

            return new_list

        if item_type == 'set':
            item_set = set(Util.string_to_list(item))

            new_set = set()

            for i in item_set:
                new_set.add(self.validate_item(i, validation, validation_failure_info))

            return new_set
        if item_type == "event_handler":
            if validation != "str:ms":
                raise AssertionError("event_handler should use str:ms in config_spec: {}".format(spec))
            return self._validate_dict_or_omap(item_type, validation, validation_failure_info, item)
        if item_type in ('dict', 'omap'):
            return self._validate_dict_or_omap(item_type, validation, validation_failure_info, item)

        raise ConfigFileError("Invalid Type '{}' in config spec {}:{}".format(item_type,
                              validation_failure_info[0][0],
                              validation_failure_info[1]), 1, self.log.name)

    def _validate_dict_or_omap(self, item_type, validation, validation_failure_info, item):
        if ':' not in validation:
            self.validation_error(item, validation_failure_info, "Missing : in dict validator.")

        validators = validation.split(':')

        if item_type == "omap":
            item_dict = OrderedDict()
            if not isinstance(item, OrderedDict):
                self.validation_error(item, validation_failure_info, "Item is not an ordered dict. "
                                                                     "Did you forget to add !!omap to your entry?",
                                      7)
        else:
            item_dict = dict()

            # item could be str, list, or list of dicts
            try:
                item = Util.event_config_to_dict(item)
            except TypeError:
                self.validation_error(item, validation_failure_info, "Could not convert item to dict", 8)

        for k, v in item.items():
            item_dict[self.validate_item(k, validators[0], validation_failure_info)] = (
                self.validate_item(v, validators[1], (validation_failure_info, k)))
        return item_dict

    def check_for_invalid_sections(self, spec, config,
                                   validation_failure_info):
        """Check if all attributes are defined in spec."""
        try:
            for k in config:
                if not isinstance(k, dict):
                    if k not in spec and k[0] != '_':

                        path_list = validation_failure_info[0].split(':')

                        if len(path_list) > 1 and path_list[-1] == validation_failure_info[1]:
                            path_list.append('[list_item]')
                        elif path_list[0] == validation_failure_info[1]:
                            path_list = list()

                        path_list.append(validation_failure_info[1])
                        path_list.append(k)

                        path_string = ':'.join(path_list)

                        if self.machine.machine_config['mpf']['allow_invalid_config_sections']:

                            self.log.warning('Unrecognized config setting. "%s" is '
                                             'not a valid setting name.',
                                             path_string)

                        else:
                            self.log.error('Your config contains a value for the '
                                           'setting "%s", but this is not a valid '
                                           'setting name.', path_string)

                            raise ConfigFileError('Your config contains a value for the '
                                                  'setting "' + path_string + '", but this is not a valid '
                                                                              'setting name.', 2, self.log.name)

        except TypeError:
            raise ConfigFileError(
                'Error in config. Your "{}:" section contains a value that is '
                'not a parent with sub-settings: {}'.format(
                    validation_failure_info[0], config), 3, self.log.name)

    def _validate_type_subconfig(self, item, param, validation_failure_info):
        if item is None:
            return {}
        try:
            attribute, base_spec_str = param.split(",", 1)
            base_spec = base_spec_str.split(",")
        except ValueError:
            base_spec = None
            attribute = param

        return self.validate_config(attribute, item, section_name=str(validation_failure_info), base_spec=base_spec)

    def _validate_type_enum(self, item, param, validation_failure_info):
        enum_values = param.lower().split(",")

        try:
            item = item.lower()
        except AttributeError:
            pass

        if item is None and "none" in enum_values:
            return None
        if item in enum_values:
            return item

        if item is False and 'no' in enum_values:
            return 'no'

        if item is True and 'yes' in enum_values:
            return 'yes'

        return self.validation_error(item, validation_failure_info,
                                     "Entry \"{}\" is not valid for enum. Valid values are: {}".format(
                                         item, str(param)))

    def _validate_type_machine(self, item, param, validation_failure_info):
        if item is None:
            return None

        section = getattr(self.machine, param, [])

        if not isinstance(item, str):
            return self.validation_error(item, validation_failure_info,
                                         "Expected {} in {} to be string".format(item, param),
                                         10)

        if item in section:
            return section[item]

        return self.validation_error(item, validation_failure_info,
                                     "Device {} of type {} not defined".format(item, param),
                                     6)

    @classmethod
    def _validate_type_list(cls, item, validation_failure_info):
        del validation_failure_info
        return Util.string_to_list(item)

    def _validate_type_int_from_hex(self, item, validation_failure_info):
        try:
            return Util.hex_string_to_int(item)
        except ValueError:
            self.validation_error(item, validation_failure_info, "Could hex convert to int")

    @classmethod
    def _validate_type_gain(cls, item, validation_failure_info):
        del validation_failure_info
        if item is None:
            return None
        return Util.string_to_gain(item)

    @classmethod
    def _validate_type_str(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return str(item)

        return None

    @classmethod
    def _validate_type_lstr(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return str(item).lower()

        return None

    def _validate_type_template_str(self, item, validation_failure_info):
        del validation_failure_info
        if item is None:
            return None

        return self.machine.placeholder_manager.build_quoted_string_template(str(item))

    def _validate_type_template_float(self, item, validation_failure_info):
        if item is None:
            return None
        if not isinstance(item, (str, float, int)):
            self.validation_error(item, validation_failure_info, "Template has to be string/int/float.")

        return self.machine.placeholder_manager.build_float_template(item)

    def _validate_type_template_secs(self, item, validation_failure_info):
        if item is None:
            return None
        if not isinstance(item, (str, int)):
            self.validation_error(item, validation_failure_info, "Template has to be string/int.")

        # try to convert to float. if we fail it will be a template
        try:
            item = Util.string_to_secs(item)
        except ValueError:
            pass

        return self.machine.placeholder_manager.build_float_template(item)

    def _validate_type_template_ms(self, item, validation_failure_info):
        if item is None:
            return None
        if not isinstance(item, (str, int)):
            self.validation_error(item, validation_failure_info, "Template has to be string/int.")

        # try to convert to int. if we fail it will be a template
        try:
            item = Util.string_to_ms(item)
        except ValueError:
            pass

        return self.machine.placeholder_manager.build_int_template(item)

    def _validate_type_template_int(self, item, validation_failure_info):
        if item is None:
            return None
        if not isinstance(item, (str, int)):
            self.validation_error(item, validation_failure_info, "Template has to be string/int.")
        return self.machine.placeholder_manager.build_int_template(item)

    def _validate_type_template_bool(self, item, validation_failure_info):
        if item is None:
            return None
        if not isinstance(item, (str, bool)):
            self.validation_error(item, validation_failure_info, "Template has to be string/bool.")

        return self.machine.placeholder_manager.build_bool_template(item)

    def _validate_type_float(self, item, validation_failure_info, param=None):
        if item is None:
            return None
        try:
            value = float(item)
        except (TypeError, ValueError):
            self.validation_error(item, validation_failure_info, "Could not convert to float")

        if param:
            param = param.split(",")
            if param[0] != "NONE" and value < float(param[0]):
                self.validation_error(item, validation_failure_info, "{} is smaller then {}".format(item, param[0]))
            elif param[1] != "NONE" and value > float(param[1]):
                self.validation_error(item, validation_failure_info, "{} is larger then {}".format(item, param[1]))

        return value

    def _validate_type_int(self, item, validation_failure_info, param=None):
        if item is None:
            return None

        try:
            value = int(item)
        except (TypeError, ValueError):
            return self.validation_error(item, validation_failure_info, "Could not convert {} to int".format(item))

        if param:
            param = param.split(",")
            if param[0] != "NONE" and value < int(param[0]):
                self.validation_error(item, validation_failure_info, "{} is smaller then {}".format(item, param[0]))
            elif param[1] != "NONE" and value > int(param[1]):
                self.validation_error(item, validation_failure_info, "{} is larger then {}".format(item, param[1]))

        return value

    def _validate_type_num(self, item, validation_failure_info, param=None):
        if item is None:
            return None

        # used for int or float, but does not convert one to the other
        if isinstance(item, (int, float)):
            value = item
        else:
            try:
                if '.' in item:
                    value = float(item)
                else:
                    value = int(item)
            except (TypeError, ValueError):
                return self.validation_error(item, validation_failure_info, "Could not convert {} to num".format(item))

        if param:
            param = param.split(",")
            if param[0] != "NONE" and value < int(param[0]):
                self.validation_error(item, validation_failure_info, "{} is smaller then {}".format(item, param[0]))
            elif param[1] != "NONE" and value > int(param[1]):
                self.validation_error(item, validation_failure_info, "{} is larger then {}".format(item, param[1]))

        return value

    @classmethod
    def _validate_type_bool(cls, item, validation_failure_info, param=None):
        assert not param
        del validation_failure_info
        if item is None:
            return None
        if isinstance(item, str):
            return item.lower() not in ['false', 'f', 'no', 'disable', 'off']
        if not item:
            return False

        return True

    @classmethod
    def _validate_type_ms(cls, item, validation_failure_info, param=None):
        del validation_failure_info
        assert not param
        if item is not None:
            return Util.string_to_ms(item)

        return None

    @classmethod
    def _validate_type_secs(cls, item, validation_failure_info, param=None):
        assert not param
        del validation_failure_info
        if item is not None:
            return Util.string_to_secs(item)

        return None

    def _validate_type_dict(self, item, validation_failure_info, param=None):
        if not item:
            return {}
        if not isinstance(item, dict):
            self.validation_error(item, validation_failure_info, "Item is not a dict.")

        if param:
            return self._validate_dict_or_omap("dict", param, validation_failure_info, item)

        return item

    def _validate_type_omap(self, item, validation_failure_info):
        if not item:
            return {}
        if not isinstance(item, OrderedDict):
            self.validation_error(item, validation_failure_info, "Item is not a ordered dict.")
        return item

    def _validate_type_kivycolor(self, item, validation_failure_info):
        # Validate colors that will be used by Kivy. The result is a 4-item
        # list, RGBA, with individual values from 0.0 - 1.0
        if not item:
            return None

        color_string = str(item).lower()

        if color_string[:1] == "(" and color_string[-1:] == ")":
            return color_string

        if color_string in NAMED_RGB_COLORS:
            color = list(NAMED_RGB_COLORS[color_string])

        elif Util.is_hex_string(color_string):
            color = [int(x, 16) for x in
                     re.split('([0-9a-f]{2})', color_string) if x != '']

        else:
            color = Util.string_to_list(color_string)

        for i, x in enumerate(color):
            try:
                color[i] = int(x) / 255
            except ValueError:
                self.validation_error(item, validation_failure_info, "Color could not be converted to int for kivy.")

        if len(color) == 3:
            color.append(1)

        return color

    def _validate_type_color(self, item, validation_failure_info):
        if isinstance(item, tuple):
            if len(item) != 3:
                self.validation_error(item, validation_failure_info, "Color needs three components")
            return item

        # Validates colors by name, hex, or list, into a 3-item list, RGB,
        # with individual values from 0-255
        color_string = str(item).lower()

        if color_string in NAMED_RGB_COLORS:
            return NAMED_RGB_COLORS[color_string]
        if Util.is_hex_string(color_string):
            return RGBColor.hex_to_rgb(color_string)

        color = Util.string_to_list(color_string)
        return int(color[0]), int(color[1]), int(color[2])

    def _validate_type_bool_int(self, item, validation_failure_info):
        if self._validate_type_bool(item, validation_failure_info):
            return 1
        return 0

    def _validate_type_pow2(self, item, validation_failure_info):
        if item is None:
            return None
        if not Util.is_power2(item):
            return self.validation_error(item, validation_failure_info, "Could not convert {} to pow2".format(item))
        return item

    def validate_item(self, item, validator, validation_failure_info):
        """Validate an item using a validator."""
        try:
            if item.lower() == 'none':
                item = None
        except AttributeError:
            pass

        if '(' in validator and ')' in validator[-1:] == ')':
            validator_parts = validator.split('(', maxsplit=1)
            validator = validator_parts[0]
            param = validator_parts[1][:-1]
            return self.validator_list[validator](item, validation_failure_info=validation_failure_info, param=param)
        if validator in self.validator_list:
            return self.validator_list[validator](item, validation_failure_info=validation_failure_info)

        raise ConfigFileError("Invalid Validator '{}' in config spec {}:{}".format(
                              validator,
                              validation_failure_info[0][0],
                              validation_failure_info[1]), 4, self.log.name)

    def _build_error_path(self, validation_failure_info):
        if isinstance(validation_failure_info[0], tuple):
            return "{}:{}".format(self._build_error_path(validation_failure_info[0]), validation_failure_info[1])

        return "{}:{}".format(validation_failure_info[0], validation_failure_info[1])

    def validation_error(self, item, validation_failure_info, msg="", code=None):
        """Raise a validation error with all relevant infos."""
        raise ConfigFileError("Config validation error: Entry {} = \"{}\" is not valid. {}".format(
            self._build_error_path(validation_failure_info),
            item, msg), 5 if code is None else code, self.log.name)
