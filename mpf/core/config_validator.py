"""Config specs and validator."""
import logging
import re
from collections import OrderedDict
from copy import deepcopy

from typing import Any, Union, List
from typing import Dict

from mpf.core.config_spec import mpf_config_spec
from mpf.core.rgb_color import named_rgb_colors, RGBColor
from mpf.exceptions.ConfigFileError import ConfigFileError
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.core.utility_functions import Util


class ConfigValidator(object):

    """Validates config against config specs."""

    config_spec = None      # type: Any

    def __init__(self, machine):
        """Initialise validator."""
        self.machine = machine
        self.log = logging.getLogger('ConfigValidator')

        self.validator_list = {
            "str": self._validate_type_str,
            "lstr": self._validate_type_lstr,
            "float": self._validate_type_float,
            "int": self._validate_type_int,
            "num": self._validate_type_num,
            "bool": self._validate_type_bool,
            "template_float": self._validate_type_template_float,
            "template_int": self._validate_type_template_int,
            "template_bool": self._validate_type_template_bool,
            "template_secs": self._validate_type_template_secs,
            "boolean": self._validate_type_bool,
            "ms": self._validate_type_ms,
            "secs": self._validate_type_secs,
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

        if not ConfigValidator.config_spec:
            ConfigValidator.load_config_spec()

    @classmethod
    def load_device_config_spec(cls, config_section, config_spec):
        """Load config specs for a device."""
        cls.config_spec[config_section] = YamlInterface.process(config_spec)

    @classmethod
    def load_mode_config_spec(cls, mode_string, config_spec):
        """Load config specs for a mode."""
        if '_mode_settings' not in cls.config_spec:
            cls.config_spec['_mode_settings'] = {}
        if mode_string not in cls.config_spec['_mode_settings']:
            cls.config_spec['_mode_settings'][mode_string] = YamlInterface.process(config_spec)

    @classmethod
    def load_config_spec(cls, config_spec=None):
        """Load config specs."""
        if not config_spec:
            config_spec = mpf_config_spec

        cls.config_spec = YamlInterface.process(config_spec)

    @classmethod
    def unload_config_spec(cls):
        """Unload specs."""
        # cls.config_spec = None
        pass

        # todo I had the idea that we could unload the config spec to save
        # memory, but doing so will take more thought about timing

    def _build_spec(self, config_spec, base_spec):
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

        if source is None:
            source = dict()

        if not section_name:
            section_name = config_spec  # str

        if prefix:
            validation_failure_info = (prefix + ":" + config_spec, section_name)
        else:
            validation_failure_info = (config_spec, section_name)

        this_spec = self._build_spec(config_spec, base_spec)

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
            item_type, validation, default = spec.split('|')
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

        elif item_type == 'list':
            item_list = Util.string_to_list(item)

            new_list = list()

            for i in item_list:
                new_list.append(self.validate_item(i, validation, validation_failure_info))

            return new_list

        elif item_type == 'set':
            item_set = set(Util.string_to_list(item))

            new_set = set()

            for i in item_set:
                new_set.add(self.validate_item(i, validation, validation_failure_info))

            return new_set

        elif item_type in ('dict', 'omap'):
            return self._validate_dict_or_omap(item_type, validation, validation_failure_info, item)
        else:
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
                self.validate_item(v, validators[1], validation_failure_info))
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
        elif item in enum_values:
            return item

        elif item is False and 'no' in enum_values:
            return 'no'

        elif item is True and 'yes' in enum_values:
            return 'yes'

        else:
            return self.validation_error(item, validation_failure_info,
                                         "Entry \"{}\" is not valid for enum. Valid values are: {}".format(
                                             item, str(param)))

    def _validate_type_machine(self, item, param, validation_failure_info):
        if item is None:
            return None

        section = getattr(self.machine, param, [])

        if item in section:
            return section[item]
        else:
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
        else:
            return None

    @classmethod
    def _validate_type_lstr(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return str(item).lower()
        else:
            return None

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

    def _validate_type_num(self, item, validation_failure_info):
        if item is None:
            return None

        # used for int or float, but does not convert one to the other
        if isinstance(item, (int, float)):
            return item
        else:
            try:
                if '.' in item:
                    return float(item)
                else:
                    return int(item)
            except (TypeError, ValueError):
                self.validation_error(item, validation_failure_info, "Could not convert {} to num".format(item))

    @classmethod
    def _validate_type_bool(cls, item, validation_failure_info):
        del validation_failure_info
        if item is None:
            return None
        elif isinstance(item, str):
            return item.lower() not in ['false', 'f', 'no', 'disable', 'off']
        elif not item:
            return False
        else:
            return True

    @classmethod
    def _validate_type_ms(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return Util.string_to_ms(item)
        else:
            return None

    @classmethod
    def _validate_type_secs(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return Util.string_to_secs(item)
        else:
            return None

    def _validate_type_dict(self, item, validation_failure_info):
        if not item:
            return {}
        if not isinstance(item, dict):
            self.validation_error(item, validation_failure_info, "Item is not a dict.")
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

        if color_string in named_rgb_colors:
            color = list(named_rgb_colors[color_string])

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

        if color_string in named_rgb_colors:
            return named_rgb_colors[color_string]
        elif Util.is_hex_string(color_string):
            return RGBColor.hex_to_rgb(color_string)

        else:
            color = Util.string_to_list(color_string)
            return int(color[0]), int(color[1]), int(color[2])

    def _validate_type_bool_int(self, item, validation_failure_info):
        if self._validate_type_bool(item, validation_failure_info):
            return 1
        else:
            return 0

    def _validate_type_pow2(self, item, validation_failure_info):
        if item is None:
            return None
        if not Util.is_power2(item):
            return self.validation_error(item, validation_failure_info, "Could not convert {} to pow2".format(item))
        else:
            return item

    def validate_item(self, item, validator, validation_failure_info):
        """Validate an item using a validator."""
        try:
            if item.lower() == 'none':
                item = None
        except AttributeError:
            pass

        if '(' in validator and ')' in validator[-1:] == ')':
            validator_parts = validator.split('(')
            validator = validator_parts[0]
            param = validator_parts[1][:-1]
            return self.validator_list[validator](item, validation_failure_info=validation_failure_info, param=param)
        elif validator in self.validator_list:
            return self.validator_list[validator](item, validation_failure_info=validation_failure_info)

        else:
            raise ConfigFileError("Invalid Validator '{}' in config spec {}:{}".format(
                                  validator,
                                  validation_failure_info[0][0],
                                  validation_failure_info[1]), 4, self.log.name)

    def _build_error_path(self, validation_failure_info):
        if isinstance(validation_failure_info[0], tuple):
            return "{}:{}".format(self._build_error_path(validation_failure_info[0]), validation_failure_info[1])
        else:
            return "{}:{}".format(validation_failure_info[0], validation_failure_info[1])

    def validation_error(self, item, validation_failure_info, msg="", code=None):
        """Raise a validation error with all relevant infos."""
        raise ConfigFileError("Config validation error: Entry {} = \"{}\" is not valid. {}".format(
            self._build_error_path(validation_failure_info),
            item, msg), 5 if code is None else code, self.log.name)
