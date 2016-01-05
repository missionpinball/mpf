"""Contains the Config class with utility configuration methods"""

# config.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import sys

import ruamel.yaml as yaml

from mpf.file_interfaces.yaml_interface import MpfLoader
from mpf.system.file_manager import FileManager
from mpf.system.timing import Timing
from mpf.system.utility_functions import Util
import version

log = logging.getLogger('ConfigProcessor')



class CaseInsensitiveDict(dict):
    """A class based on Python's 'dict' class that internally stores all keys
    as lowercase. Set, get, contains, and del methods have been overwritten to
    automatically convert incoming calls to lowercase.
    """
    def __setitem__(self, key, value):
        try:
            super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)
        except AttributeError:
            super(CaseInsensitiveDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        try:
            return super(CaseInsensitiveDict, self).__getitem__(key.lower())
        except AttributeError:
            return super(CaseInsensitiveDict, self).__getitem__(key)

    def __contains__(self, key):
        try:
            return super(CaseInsensitiveDict, self).__contains__(key.lower())
        except AttributeError:
            return super(CaseInsensitiveDict, self).__contains__(key)

    def __delitem__(self, key):
        try:
            return super(CaseInsensitiveDict, self).__delitem__(key.lower())
        except AttributeError:
            return super(CaseInsensitiveDict, self).__delitem__(key)


class Config(object):

    config_spec = None

    def __init__(self, machine, system_config=None):
        self.machine = machine
        self.log = logging.getLogger('ConfigProcessor')

        if not system_config:
            self.system_config = self.machine.config['mpf']
        else:
            self.system_config = system_config

    @classmethod
    def load_config_spec(cls):
        cls.config_spec = cls.load_config_file('mpf/config_validator.yaml')

    @classmethod
    def unload_config_spec(cls):
        cls.config_spec = None

    @staticmethod
    def set_machine_path(machine_path, machine_files_default='machine_files'):
        # If the machine folder value passed starts with a forward or
        # backward slash, then we assume it's from the mpf root. Otherwise we
        # assume it's in the mpf/machine_files folder
        if (machine_path.startswith('/') or machine_path.startswith('\\')):
            machine_path = machine_path
        else:
            machine_path = os.path.join(machine_files_default, machine_path)

        machine_path = os.path.abspath(machine_path)
        logging.info("Machine path: {}".format(machine_path))

        # Add the machine folder to sys.path so we can import modules from it
        sys.path.append(machine_path)
        return machine_path

    @staticmethod
    def load_machine_config(config_file_list, machine_path,
                             config_path='config', existing_config=None):
        for num, config_file in enumerate(config_file_list):

            if not existing_config:
                machine_config = CaseInsensitiveDict()
            else:
                machine_config = existing_config

            if not (config_file.startswith('/') or
                    config_file.startswith('\\')):

                config_file = os.path.join(machine_path, config_path,
                                           config_file)

            logging.info("Machine config file #%s: %s", num+1, config_file)

            machine_config = Util.dict_merge(machine_config,
                Config.load_config_file(config_file))

        return machine_config

    @staticmethod
    def load_config_file(filename, verify_version=True, halt_on_error=True):
        config = FileManager.load(filename, verify_version, halt_on_error)

        try:
            if 'config' in config:
                path = os.path.split(filename)[0]

                for file in Util.string_to_list(config['config']):
                    full_file = os.path.join(path, file)
                    config = Util.dict_merge(config,
                                               Config.load_config_file(full_file))
            return config
        except TypeError:
            return dict()

    @staticmethod
    def process_config(config_spec, source, target=None):  # pragma: no cover
        # Note this method is deprecated and will be removed eventually
        # Use process_config2() instead
        config_spec = yaml.load(config_spec, Loader=MpfLoader)
        processed_config = source

        for k in list(config_spec.keys()):
            if k in source:
                processed_config[k] = Config.validate_config_item(
                    config_spec[k], source[k])
            else:
                log.debug('Processing default settings for key "%s:"', k)
                processed_config[k] = Config.validate_config_item(
                    config_spec[k])

        if target:
            processed_config = Util.dict_merge(target, processed_config)

        return processed_config

    @staticmethod
    def validate_config_item(spec, item='item not in config!@#'):  # pragma: no cover
        # Note this method is deprecated and will be removed eventually
        # Use validate_config_item2() instead

        try:
            if item.lower() == 'none':
                item = None
        except AttributeError:
            pass

        default = 'default required!@#'

        if '|' in spec:
            item_type, default = spec.split('|')
            if type(default) is str and default.lower() == 'none':
                default = None
        else:
            item_type = spec

        if item == 'item not in config!@#':
            if default == 'default required!@#':
                log.error('Required setting missing from config file. Run with '
                          'verbose logging and look for the last '
                          'ConfigProcessor entry above this line to see where '
                          'the problem is.')
                sys.exit()
            else:
                item = default

        if item_type == 'list':
            return Util.string_to_list(item)

        if item_type == 'list_of_dicts':
            if type(item) is list:
                return item
            elif type(item) is dict:
                return [item]

        elif item_type == 'set':
            return set(Util.string_to_list(item))

        elif item_type == 'dict':
            if type(item) is dict or type(item) is CaseInsensitiveDict:
                return item
            elif not default:
                return dict()
            else:
                log.error('Config error. "%s" is not a dictionary', item)
                sys.exit()

        elif item_type == 'int':
            try:
                return int(item)
            except TypeError:
                return None

        elif item_type == 'float':
            try:
                return float(item)
            except TypeError:
                return None

        elif item_type in ('string', 'str'):

            if item:
                return str(item)
            else:
                return None

        elif item_type in ('boolean', 'bool'):
            if type(item) is bool:
                return item
            else:
                return str(item).lower() in ('yes', 'true')

        elif item_type == 'ms':
            return Timing.string_to_ms(item)

        elif item_type == 'secs':
            return Timing.string_to_secs(item)

        elif item_type == 'list_of_lists':
            return Util.list_of_lists(item)

    def process_config2(self, config_spec, source, section_name=None,
                        target=None, result_type='dict'):
        # config_spec, str i.e. "device:shot"
        # source is dict
        # section_name is str used for logging failures

        if not self.config_spec:
            self.load_config_spec()

        if not section_name:
            section_name = config_spec

        validation_failure_info = (config_spec, section_name)

        orig_spec = config_spec

        config_spec = config_spec.split(':')
        this_spec = self.config_spec

        for i in range(len(config_spec)):
            this_spec = this_spec[config_spec[i]]

        self.check_for_invalid_sections(this_spec, source,
                                        validation_failure_info)

        processed_config = source

        for k in list(this_spec.keys()):
            if k in source:  # validate the entry that exists

                if type(this_spec[k]) is dict:
                    # This means we're looking for a list of dicts

                    final_list = list()
                    if k in source:
                        for i in source[k]:  # individual step
                            final_list.append(self.process_config2(
                                orig_spec + ':' + k, source=i, section_name=k))

                    processed_config[k] = final_list

                elif result_type == 'list':
                    # spec is dict
                    # item is source
                    processed_config = self.validate_config_item2(
                        spec=this_spec[k], item=source[k],
                        validation_failure_info=(validation_failure_info, k))

                else:
                    processed_config[k] = self.validate_config_item2(
                        this_spec[k], item=source[k],
                        validation_failure_info=(validation_failure_info, k))

            else:  # create the default entry

                if type(this_spec[k]) is dict:
                    processed_config[k] = list()

                else:
                    if result_type == 'list':
                        processed_config = self.validate_config_item2(
                            this_spec[k],
                            validation_failure_info=(validation_failure_info,
                                                     k))

                    else:
                        processed_config[k] = self.validate_config_item2(
                            this_spec[k],
                            validation_failure_info=(validation_failure_info,
                                                     k))

        if target:
            processed_config = Util.dict_merge(target, processed_config)

        #if result_type == 'list':
            #quit()

        return processed_config

    def validate_config_item2(self, spec, validation_failure_info,
                              item='item not in config!@#',):

        try:
            item_type, validation, default = spec.split('|')
        except ValueError:
            raise ValueError('Error in validator config: {}'.format(spec))

        if default.lower() == 'none':
            default = None
        elif not default:
            default = 'default required!@#'

        if item == 'item not in config!@#':
            if default == 'default required!@#':
                raise ValueError('Required setting missing from config file. '
                    'Run with verbose logging and look for the last '
                    'ConfigProcessor entry above this line to see where the '
                    'problem is. {} {}'.format(spec, validation_failure_info))
            else:
                item = default

        if item_type == 'single':
            item = self.validate_item(item, validation, validation_failure_info)

        elif item_type == 'list':
            item = Util.string_to_list(item)

            new_list = list()

            for i in item:
                new_list.append(
                    self.validate_item(i, validation, validation_failure_info))

            item = new_list

        elif item_type == 'set':
            item = set(Util.string_to_list(item))

            new_set = set()

            for i in item:
                new_set.add(
                    self.validate_item(i, validation, validation_failure_info))

            item = new_set

        elif item_type == 'dict':
            item = self.validate_item(item, validation,
                                      validation_failure_info)

            if not item:
                item = dict()

        else:
            self.log.error("Invalid Type '%s' in config spec %s:%s", item_type,
                           validation_failure_info[0][0],
                           validation_failure_info[1])
            sys.exit()

        return item

    def check_for_invalid_sections(self, spec, config, validation_failure_info):

        for k, v in config.items():
            if type(k) is not dict:

                if k not in spec:

                    path_list = validation_failure_info[0].split(':')

                    if len(path_list) > 1 and (
                            path_list[-1] == validation_failure_info[1]):
                        path_list.append('[list_item]')
                    elif path_list[0] == validation_failure_info[1]:
                        path_list = list()

                    path_list.append(validation_failure_info[1])
                    path_list.append(k)

                    path_string = ':'.join(path_list)

                    if self.system_config['allow_invalid_config_sections']:

                        self.log.warning('Unrecognized config setting. "%s" is '
                                         'not a valid setting name.',
                                         path_string)

                    else:
                        self.log.error('Your config contains a value for the '
                                       'setting "%s", but this is not a valid '
                                       'setting name.', path_string)

                        self.lookup_invalid_config_setting(path_string)

                        sys.exit()

    def validate_item(self, item, validator, validation_failure_info):

        try:
            if item.lower() == 'none':
                item = None
        except AttributeError:
            pass

        if ':' in validator:
            validator = validator.split(':')
            # item could be str, list, or list of dicts
            item = Util.event_config_to_dict(item)

            return_dict = dict()

            for k, v in item.items():
                return_dict[self.validate_item(k, validator[0],
                                               validation_failure_info)] = (
                    self.validate_item(v, validator[1], validation_failure_info)
                    )

            item = return_dict

        elif '%' in validator:

            if type(item) is str:

                try:
                    item = eval(validator.replace('%', "'" + item + "'"))
                except KeyError:
                    self.validation_error(item, validation_failure_info)
            else:
                item = None

        elif validator == 'str':
            if item is not None:
                item = str(item)
            else:
                item = None

        elif validator == 'float':
            try:
                item = float(item)
            except (TypeError, ValueError):
                # TODO error
                pass

        elif validator == 'int':
            try:
                item = int(item)
            except (TypeError, ValueError):
                # TODO error
                pass

        elif validator in ('bool', 'boolean'):
            if type(item) is str:
                if item.lower() in ['false', 'f', 'no', 'disable', 'off']:
                    item = False

            elif not item:
                item = False

            else:
                item = True

        elif validator == 'ms':
            item = Timing.string_to_ms(item)

        elif validator == 'secs':
            item = Timing.string_to_secs(item)

        elif validator == 'ticks':
            item = Timing.string_to_ticks(item)

        elif validator == 'ticks_int':
            item = int(Timing.string_to_ticks(item))

        elif validator == 'list':
            item = Util.string_to_list(item)

        else:
            self.log.error("Invalid Validator '%s' in config spec %s:%s",
                           validator,
                           validation_failure_info[0][0],
                           validation_failure_info[1])
            sys.exit()

        return item

    def validation_error(self, item, validation_failure_info):
        self.log.error("Config validation error: Entry %s:%s:%s:%s is not valid",
                       validation_failure_info[0][0],
                       validation_failure_info[0][1],
                       validation_failure_info[1],
                       item)

        sys.exit()

    def lookup_invalid_config_setting(self, setting):

        setting_key = setting.split(':')[-1]

        with open(self.system_config['config_versions_file'], 'r') as f:
            config_file = yaml.load(f, Loader=MpfLoader)

        for ver, sections in config_file.items():

            if type(ver) is not int:
                continue

            ver_string = ''

            if int(version.__config_version_info__) > int(ver):
                ver_string = (' (The latest config version is config_version=' +
                              version.__config_version_info__ + ').')

            if setting_key in sections['section_replacements']:
                self.log.info('The setting "%s" has been renamed to "%s" in '
                              'config_version=%s%s', setting,
                              sections['section_replacements'][setting_key],
                              ver, ver_string)
            if setting_key in sections['section_deprecations']:
                self.log.info('The setting "%s" has been removed in '
                              'config_version=%s%s', setting, ver, ver_string)

        if setting in config_file['custom_messages']:
            self.log.info(config_file['custom_messages'][setting])


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
