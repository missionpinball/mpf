"""Contains the Config class with utility configuration methods"""

# config.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import sys

import yaml
from copy import deepcopy

from mpf.system.timing import Timing
import mpf.config_file_interfaces
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

    def __init__(self, machine):
        self.machine = machine

    @classmethod
    def init(cls):
        cls.config_file_processors = dict()

        for module in mpf.config_file_interfaces.__all__:

                __import__('mpf.config_file_interfaces.{}'.format(module))

                interface_class = eval(
                    'mpf.config_file_interfaces.{}.file_interface_class'.format(module))

                this_instance = interface_class()

                for file_type in interface_class.file_types:
                    cls.config_file_processors[file_type] = this_instance



    @staticmethod
    def load_config_file(filename):
        ext = os.path.splitext(filename)[1]

        if not os.path.isfile(filename):
            # If the file doesn't have an extension, let's see if we can find
            # one
            if not ext:
                for config_processor in set(Config.config_file_processors.values()):
                    questionable_file, ext = config_processor.find_file(filename)
                    if questionable_file:
                        filename = questionable_file
                        break

        try:
            return Config.config_file_processors[ext].load(filename)
        except KeyError:
            # todo convert to exception
            print "No config file processor available for file type {}".format(ext)
            sys.exit()

    @staticmethod
    def load_config_file(filename):
        ext = os.path.splitext(filename)[1]

        if not os.path.isfile(filename):
            # If the file doesn't have an extension, let's see if we can find
            # one
            if not ext:
                for config_processor in set(Config.config_file_processors.values()):
                    questionable_file, ext = config_processor.find_file(filename)
                    if questionable_file:
                        filename = questionable_file
                        break

        try:
            config =  Config.config_file_processors[ext].load(filename)
        except KeyError:
            # todo convert to exception
            log.error("No config file processor available for file type {}"
                      .format(ext))
            sys.exit()

        if 'config' in config:
            path = os.path.split(filename)[0]

            for file in Config.string_to_list(config['config']):
                full_file = os.path.join(path, file)
                config = Config.dict_merge(config,
                                           Config.load_config_file(full_file))

        return config

    @staticmethod
    def keys_to_lower(source_dict):
        """Converts the keys of a dictionary to lowercase.

        Args:
            source_dict: The dictionary you want to convert.

        Returns:
            A dictionary with lowercase keys.
        """

        if type(source_dict) is None:
            return dict()
        elif not source_dict:
            return

        for k in source_dict.keys():
            if type(source_dict[k]) is dict:
                source_dict[k] = Config.keys_to_lower(source_dict[k])

        return dict((str(k).lower(), v) for k, v in source_dict.iteritems())

    @staticmethod
    def process_config(config_spec, source, target=None):
        config_spec = yaml.load(config_spec)
        processed_config = source

        for k in config_spec.keys():
            if k in source:
                processed_config[k] = Config.validate_config_item(
                    config_spec[k], source[k])
            else:
                log.debug('Processing default settings for key "%s:"', k)
                processed_config[k] = Config.validate_config_item(
                    config_spec[k])

        if target:
            processed_config = Config.dict_merge(target, processed_config)

        return processed_config

    @staticmethod
    def validate_config_item(spec, item='item not in config!@#'):

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
            return Config.string_to_list(item)

        if item_type == 'list_of_dicts':
            if type(item) is list:
                return item
            elif type(item) is dict:
                return [item]

        elif item_type == 'set':
            return set(Config.string_to_list(item))

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
            return Config.list_of_lists(item)

    @staticmethod
    def chunker(l, n):
        """Yields successive n-sized chunks from l."""
        for i in xrange(0, len(l), n):
            yield l[i:i+n]

    def process_config2(self, config_spec, source, section_name=None,
                        target=None, result_type='dict'):
        # config_spec, str i.e. "device:shot"
        # source is dict
        # section_name is str used for logging failures

        if not section_name:
            section_name = config_spec

        validation_failure_info = (config_spec, section_name)

        orig_spec = config_spec

        config_spec = config_spec.split(':')
        this_spec = self.machine.config['config_validator']

        for i in range(len(config_spec)):
            this_spec = this_spec[config_spec[i]]

        self.check_for_invalid_sections(this_spec, source,
                                        validation_failure_info)

        processed_config = source

        for k in this_spec.keys():
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
            processed_config = Config.dict_merge(target, processed_config)

        #if result_type == 'list':
            #quit()

        return processed_config

    def validate_config_item2(self, spec, validation_failure_info,
                              item='item not in config!@#',):

        default = 'default required!@#'

        item_type, validation, default = spec.split('|')

        if default.lower() == 'none':
            default = None

        if item == 'item not in config!@#':
            if default == 'default required!@#':
                log.error('Required setting missing from config file. Run with '
                          'verbose logging and look for the last '
                          'ConfigProcessor entry above this line to see where '
                          'the problem is.')
                sys.exit()
            else:
                item = default

        if item_type == 'single':
            item = self.validate_item(item, validation, validation_failure_info)


        elif item_type == 'list':
            item = Config.string_to_list(item)

            new_list = list()

            for i in item:
                new_list.append(
                    self.validate_item(i, validation, validation_failure_info))

            item = new_list

        elif item_type == 'set':
            item = set(Config.string_to_list(item))

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

        for k, v in config.iteritems():
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

                    if (self.machine.config['mpf']
                            ['allow_invalid_config_sections']):

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
            item = Config.event_config_to_dict(item)

            return_dict = dict()

            for k, v in item.iteritems():
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

        elif validator == 'bool':

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

        with open(self.machine.config['mpf']['config_versions_file'],
                  'r') as f:

            config_file = yaml.load(f)

        for ver, sections in config_file.iteritems():

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


    @staticmethod
    def dict_merge(a, b, combine_lists=True):
        """Recursively merges dictionaries.

        Used to merge dictionaries of dictionaries, like when we're merging
        together the machine configuration files. This method is called
        recursively as it finds sub-dictionaries.

        For example, in the traditional python dictionary
        update() methods, if a dictionary key exists in the original and
        merging-in dictionary, the new value will overwrite the old value.

        Consider the following example:

        Original dictionary:
        `config['foo']['bar'] = 1`

        New dictionary we're merging in:
        `config['foo']['other_bar'] = 2`

        Default python dictionary update() method would have the updated
        dictionary as this:

        `{'foo': {'other_bar': 2}}`

        This happens because the original dictionary which had the single key
        `bar` was overwritten by a new dictionary which has a single key
        `other_bar`.)

        But really we want this:

        `{'foo': {'bar': 1, 'other_bar': 2}}`

        This code was based on this:
        https://www.xormedia.com/recursively-merge-dictionaries-in-python/

        Args:
            a (dict): The first dictionary
            b (dict): The second dictionary
            combine_lists (bool):
                Controls whether lists should be combined (extended) or
                overwritten. Default is `True` which combines them.

        Returns:
            The merged dictionaries.
        """
        #log.info("Dict Merge incoming A %s", a)
        #log.info("Dict Merge incoming B %s", b)
        if not isinstance(b, dict):
            return b
        result = deepcopy(a)
        for k, v in b.iteritems():
            if k in result and isinstance(result[k], dict):
                result[k] = Config.dict_merge(result[k], v)
            elif k in result and isinstance(result[k], list) and combine_lists:
                result[k].extend(v)
            else:
                result[k] = deepcopy(v)
        #log.info("Dict Merge result: %s", result)
        return result

    @staticmethod
    def string_to_list(string):
        """ Converts a comma-separated and/or space-separated string into a
        Python list.

        Args:
            string: The string you'd like to convert.

        Returns:
            A python list object containing whatever was between commas and/or
            spaces in the string.
        """
        if type(string) is str:
            # Convert commas to spaces, then split the string into a list
            new_list = string.replace(',', ' ').split()
            # Look for string values of "None" and convert them to Nonetypes.
            for index, value in enumerate(new_list):
                if type(value) is str and value.lower() == 'none':
                    new_list[index] = None
            return new_list

        elif type(string) is list:
            return string  # If it's already a list, do nothing

        elif string is None:
            return []  # If it's None, make it into an empty list
        else:
            # if we're passed anything else, just make it into a list
            return [string]

    @staticmethod
    def string_to_lowercase_list(string):
        """ Converts a comma-separated and/or space-separated string into a
        Python list where each item in the list has been converted to lowercase.

        Args:
            string: The string you'd like to convert.

        Returns:
            A python list object containing whatever was between commas and/or
            spaces in the string, with each item converted to lowercase.
        """
        new_list = Config.string_to_list(string)

        new_list = [x.lower() for x in new_list]

        return new_list

    @staticmethod
    def list_of_lists(incoming_string):
        """ Converts an incoming string or list into a list of lists. """
        final_list = list()

        if type(incoming_string) is str:
            final_list = [Config.string_to_list(incoming_string)]

        else:
            for item in incoming_string:
                final_list.append(Config.string_to_list(item))

        return final_list

    @staticmethod
    def hexstring_to_list(input_string, output_length=3):
        """Takes a string input of hex numbers and returns a list of integers.

        This always groups the hex string in twos, so an input of ffff00 will
        be returned as [255, 255, 0]

        Args:
            input_string: A string of incoming hex colors, like ffff00.
            output_length: Integer value of the number of items you'd like in
                your returned list. Default is 3. This method will ignore
                extra characters if the input_string is too long, and it will
                pad with zeros if the input string is too short.

        Returns:
            List of integers, like [255, 255, 0]

        """
        output = []
        input_string = str(input_string).zfill(output_length*2)

        for i in xrange(0, len(input_string), 2):  # step through every 2 chars
            output.append(int(input_string[i:i+2], 16))

        return output[0:output_length:]

    @staticmethod
    def hexstring_to_int(inputstring, maxvalue=255):
        """Takes a string input of hex numbers and an integer.

        Args:
            input_string: A string of incoming hex colors, like ffff00.
            maxvalue: Integer of the max value you'd like to return. Default is
                255. (This is the real value of why this method exists.)

        Returns:
            Integer representation of the hex string.
        """

        return_int = int(inputstring, 16)

        if return_int > maxvalue:
            return_int = maxvalue

        return return_int

    @staticmethod
    def event_config_to_dict(config):

        return_dict = dict()

        if type(config) is dict:
            return config
        elif type(config) is str:
            config = Config.string_to_list(config)

        # 'if' instead of 'elif' to pick up just-converted str
        if type(config) is list:
            for event in config:
                return_dict[event] = 0

        return return_dict

    @staticmethod
    def int_to_hex_string(source_int):
        """Converts an int from 0-255 to a one-byte (2 chars) hex string, with
        uppercase characters.

        """

        source_int = int(source_int)

        if 0 <= source_int <= 255:
            return format(source_int, 'x').upper().zfill(2)

        else:
            raise ValueError("invalid source int: %s" % (source_int))

    @staticmethod
    def pwm8_to_hex_string(source_int):

        lookup_table = {
                        0: '00',  # 00000000
                        1: '01',  # 00000001
                        2: '88',  # 10001000
                        3: '92',  # 10010010
                        4: 'AA',  # 10101010
                        5: 'BA',  # 10111010
                        6: 'EE',  # 11101110
                        7: 'FE',  # 11111110
                        8: 'FF',  # 11111111
                        }

        if 0 <= source_int <= 8:
            return lookup_table[source_int]
        else:
            raise ValueError("%s is invalid pwm hex value. (Expected value "
                             "0-8)" % (source_int))

    @staticmethod
    def pwm32_to_hex_string(source_int):

        # generated by the int_to_pwm.py script in the mpf/tools folder

        lookup_table = {
                        0: '00000000',   # 00000000000000000000000000000000
                        1: '00000002',   # 00000000000000000000000000000010
                        2: '00020002',   # 00000000000000100000000000000010
                        3: '00400802',   # 00000000010000000000100000000010
                        4: '02020202',   # 00000010000000100000001000000010
                        5: '04102082',   # 00000100000100000010000010000010
                        6: '08420842',   # 00001000010000100000100001000010
                        7: '10884422',   # 00010000100010000100010000100010
                        8: '22222222',   # 00100010001000100010001000100010
                        9: '22448912',   # 00100010010001001000100100010010
                        10: '24922492',  # 00100100100100100010010010010010
                        11: '4924924a',  # 01001001001001001001001001001010
                        12: '4a4a4a4a',  # 01001010010010100100101001001010
                        13: '5294a52a',  # 01010010100101001010010100101010
                        14: '54aa54aa',  # 01010100101010100101010010101010
                        15: '5554aaaa',  # 01010101010101001010101010101010
                        16: 'aaaaaaaa',  # 10101010101010101010101010101010
                        17: 'aaab5556',  # 10101010101010110101010101010110
                        18: 'ab56ab56',  # 10101011010101101010101101010110
                        19: 'ad6b5ad6',  # 10101101011010110101101011010110
                        20: 'b6b6b6b6',  # 10110110101101101011011010110110
                        21: 'b6db6db6',  # 10110110110110110110110110110110
                        22: 'db6edb6e',  # 11011011011011101101101101101110
                        23: 'ddbb76ee',  # 11011101101110110111011011101110
                        24: 'eeeeeeee',  # 11101110111011101110111011101110
                        25: 'ef77bbde',  # 11101111011101111011101111011110
                        26: 'f7bef7be',  # 11110111101111101111011110111110
                        27: 'fbefdf7e',  # 11111011111011111101111101111110
                        28: 'fefefefe',  # 11111110111111101111111011111110
                        29: 'ffbff7fe',  # 11111111101111111111011111111110
                        30: 'fffefffe',  # 11111111111111101111111111111110
                        31: 'fffffffe',  # 11111111111111111111111111111110
                        32: 'ffffffff',  # 11111111111111111111111111111111
                        }

        if 0 <= source_int <= 32:
            return lookup_table[source_int]
        else:
            raise ValueError("%s is invalid pwm hex value. (Expected value "
                             "0-32)" % (source_int))

    @staticmethod
    def pwm32_to_int(source_int):

        # generated by the int_to_pwm.py script in the mpf/tools folder

        lookup_table = {
                        0: 0,            # 00000000000000000000000000000000
                        1: 2,            # 00000000000000000000000000000010
                        2: 131074,       # 00000000000000100000000000000010
                        3: 4196354,      # 00000000010000000000100000000010
                        4: 33686018,     # 00000010000000100000001000000010
                        5: 68165762,     # 00000100000100000010000010000010
                        6: 138545218,    # 00001000010000100000100001000010
                        7: 277365794,    # 00010000100010000100010000100010
                        8: 572662306,    # 00100010001000100010001000100010
                        9: 574916882,    # 00100010010001001000100100010010
                        10: 613557394,   # 00100100100100100010010010010010
                        11: 1227133514,  # 01001001001001001001001001001010
                        12: 1246382666,  # 01001010010010100100101001001010
                        13: 1385473322,  # 01010010100101001010010100101010
                        14: 1420448938,  # 01010100101010100101010010101010
                        15: 1431612074,  # 01010101010101001010101010101010
                        16: 2863311530,  # 10101010101010101010101010101010
                        17: 2863355222,  # 10101010101010110101010101010110
                        18: 2874583894,  # 10101011010101101010101101010110
                        19: 2909493974,  # 10101101011010110101101011010110
                        20: 3065427638,  # 10110110101101101011011010110110
                        21: 3067833782,  # 10110110110110110110110110110110
                        22: 3681475438,  # 11011011011011101101101101101110
                        23: 3720050414,  # 11011101101110110111011011101110
                        24: 4008636142,  # 11101110111011101110111011101110
                        25: 4017601502,  # 11101111011101111011101111011110
                        26: 4156487614,  # 11110111101111101111011110111110
                        27: 4226801534,  # 11111011111011111101111101111110
                        28: 4278124286,  # 11111110111111101111111011111110
                        29: 4290770942,  # 11111111101111111111011111111110
                        30: 4294901758,  # 11111111111111101111111111111110
                        31: 4294967294,  # 11111111111111111111111111111110
                        32: 4294967295,  # 11111111111111111111111111111111
                        }

        if 0 <= source_int <= 32:
            return lookup_table[source_int]
        else:
            raise ValueError("%s is invalid pwm int value. (Expected value "
                             "0-32)" % (source_int))

    @staticmethod
    def pwm8_to_int(source_int):
        lookup_table = {
                        0: 0,    # 00000000
                        1: 1,    # 00000001
                        2: 136,  # 10001000
                        3: 146,  # 10010010
                        4: 170,  # 10101010
                        5: 186,  # 10111010
                        6: 238,  # 11101110
                        7: 254,  # 11111110
                        8: 255,  # 11111111
                        }

        if 0 <= source_int <= 8:
            return lookup_table[source_int]
        else:
            raise ValueError("Invalid pwm value. (Expected value 0-8)")

    @staticmethod
    def pwm8_to_on_off(source_int):
        lookup_table = {
                        0: (0,0),  # 0-0
                        1: (1,7),  # 1-7
                        2: (1,3),  # 2-6
                        3: (3,5),  # 3-5
                        4: (1,1),  # 4-4
                        5: (5,3),  # 5-3
                        6: (3,1),  # 6-2
                        7: (7,1),  # 7-1
                        8: (8,0),  # 8-0
                        }

        source_int = int(source_int)

        if 0 <= source_int <= 8:
            return lookup_table[source_int]
        else:
            raise ValueError("Invalid pwm value. (Expected value 0-8)")

    @staticmethod
    def bin_str_to_hex_str(source_int_str, num_chars):
        return Config.normalize_hex_string('%0X' % int(source_int_str, 2),
                                           num_chars)

    @staticmethod
    def normalize_hex_string(source_hex, num_chars=2):
        """Takes an incoming hex value and converts it to uppercase and fills in
        leading zeros.

        Args:
            source_hex: Incoming source number. Can be any format.
            num_chars: Total number of characters that will be returned. Default
                is two.

        Returns: String, uppercase, zero padded to the num_chars.

        Example usage: Send "c" as source_hex, returns "0C".

        """
        return str(source_hex).upper().zfill(num_chars)


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
