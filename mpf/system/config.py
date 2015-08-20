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
        self.log = logging.getLogger('Config')


    @staticmethod
    def load_config_yaml(config=None, yaml_file=None,
                         new_config_dict=None):
        """Merges a new config dictionary into an existing one.

        This method does what we call a "deep merge" which means it merges
        together subdictionaries instead of overwriting them. See the
        documentation for `meth:dict_merge` for a description of how this
        works.

        If the config dictionary you're merging in also contains links to
        additional config files, it will also merge those in.

        At this point this method loads YAML files, but it would be simple to
        load them from JSON, XML, INI, or existing python dictionaires.

        Args:
            config: The optional current version of the config dictionary that
                you're building up. If you don't pass a dictionary, this method
                will create one.
            yaml_file: A YAML file containing the settings to deep merge into
                the config dictionary. This method will try to find a file
                with that name and open it to read in the settings. It will
                first try to open it as a file directly (including any path
                that's there). If that doesn't work, it will try to open the
                file using the last path that worked. (This path is stored in
                `config['config_path']`.)
            new_config_dict: A dictionary of settings to merge into the config
                dictionary.

        Note that you only need to specify a yaml_file or new_config_dictionary,
        not both.

        Returns: Python dictionary which is your source with all the new config
            options merged in.

        """

        if not config:
            config = dict()
        else:
            config = Config.keys_to_lower(config)

        new_updates = dict()

        # If we were passed a config dict, load from there
        if type(new_config_dict) == dict:
            new_updates = Config.keys_to_lower(new_config_dict)

        # If not, do we have a yaml_file?
        elif yaml_file:
            if os.path.isfile(yaml_file):
                Config.check_config_file_version(yaml_file)
                config_location = yaml_file
                # Pull out the path in case we need it later
                config['config_path'] = os.path.split(yaml_file)[0]
            elif ('config_path' in config and
                    os.path.isfile(os.path.join(config['config_path'],
                                                yaml_file))):
                config_location = os.path.join(config['config_path'],
                                               yaml_file)
            else:
                log.critical("Couldn't find file: %s.", yaml_file)
                sys.exit()

        if config_location:

            try:
                log.info("Loading configuration from file: %s", config_location)
                new_updates = Config.keys_to_lower(yaml.load(open(
                                                   config_location, 'r')))
            except yaml.YAMLError, exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    log.critical("Error found in config file %s. Line %s, "
                                 "Position %s", config_location, mark.line+1,
                                 mark.column+1)
                    sys.exit()
            except:
                log.critical("Couldn't load from file: %s", yaml_file)
                raise
                sys.exit()

        config = Config.dict_merge(config, new_updates)

        # now check if there are any more updates to do.
        # iterate and remove them

        try:
            if 'config' in config:

                if type(config['config']) is not list:
                    config['config'] = Config.string_to_list(config['config'])

                if yaml_file in config['config']:
                    config['config'].remove(yaml_file)

                if config['config']:
                    config = Config.load_config_yaml(config=config,
                                              yaml_file=config['config'][0])
        except:
            log.critical("No configuration file found, or config file is empty."
                         " But congrats! MPF works! :)")
            raise
            sys.exit()

        return config

    @staticmethod
    def check_config_file_version(file_location):
        """Checks a configuration file to see if it's the proper version for
        this version of MPF.

        Args:
            file_location: The path to the file to check.

        Returns: True if the config version of the file matches. False if not.

        This method checks that the a string 'config_version=x' exists in the
        first line of the file. If so, it checks that 'x' matches MPF's
        config_version specification.

        This check is done as integers.

        """
        with open(file_location) as f:
            file_version = f.readline().split('config_version=')[-1:][0]

            try:
                file_version = int(file_version)
            except ValueError:
                file_version = 0

            if file_version != int(version.__config_version__):
                log.error("Config file %s is version %s. MPF %s requires "
                          "version %s", file_location, file_version,
                          version.__version__, version.__config_version__)
                log.error("Use the Config File Migrator to automatically "
                          "migrate your config file to the latest version.")
                log.error("Migration tool: "
                           "https://missionpinball.com/docs/tools/config-file-migrator/")
                log.error("More info on config version %s: %s",
                          version.__config_version__,
                          version.__config_version_url__)
                sys.exit()

    @staticmethod
    def keys_to_lower(source_dict):
        """Converts the keys of a dictionary to lowercase.

        Args:
            source_dict: The dictionary you want to convert.

        Returns:
            A dictionary with lowercase keys.
        """
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
                return item.lower() in ('yes', 'true')

        elif item_type == 'ms':
            return Timing.string_to_ms(item)

        elif item_type == 'secs':
            return Timing.string_to_secs(item)

        elif item_type == 'list_of_lists':
            return Config.list_of_lists(item)

    def process_config2(self, config_spec, source, section_name, target=None,
                        result_type='dict'):
        # config_spec, str i.e. "device:shot"
        # source is dict
        # section_name is str used for logging failures

        validation_failure_info = (config_spec, section_name)

        orig_spec = config_spec


        config_spec = config_spec.split(':')
        this_spec = self.machine.config['config_validator']

        for i in range(len(config_spec)):
            this_spec = this_spec[config_spec[i]]

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
                            validation_failure_info=(validation_failure_info, k))

                    else:
                        processed_config[k] = self.validate_config_item2(
                            this_spec[k],
                            validation_failure_info=(validation_failure_info, k))

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

        if item_type == 'list':
            item = Config.string_to_list(item)

            new_list = list()

            for i in item:
                new_list.append(
                    self.validate_item(i, validation, validation_failure_info))

            item = new_list

        elif item_type == 'list_of_dicts':
            if type(item) is list:
                pass
            elif type(item) is dict:
                item = [item]

            # TODO

        elif item_type == 'single':
            item = self.validate_item(item, validation, validation_failure_info)

        elif item_type == 'delay_dict':  # time values will be ms
            if not item:
                item = dict()

            else:
                new_dict = dict()

                for k, v in item.iteritems():
                    new_dict[self.validate_item(k, validation,
                        validation_failure_info)] = Timing.string_to_ms(v)

                item = new_dict

        elif item_type == 'set':
            item = set(Config.string_to_list(item))

            new_set = set()

            for i in item:
                new_set.add(
                    self.validate_item(i, validation, validation_failure_info))

            item = new_set

        elif item_type == 'dict':
            if type(item) is dict or type(item) is CaseInsensitiveDict:
                pass
            elif not default:
                item = dict()
            else:
                log.error('Config error. "%s" is not a dictionary', item)
                sys.exit()

            # TODO

        elif item_type == 'int':

            try:
                item = int(item)
            except TypeError:
                # TODO error
                pass

        elif item_type == 'float':
            try:
                item = float(item)
            except TypeError:
                # TODO error
                pass

        elif item_type in ('boolean', 'bool'):
            if not item:
                item = False
            elif type(item) is str and item.lower() in ('no', 'false', 'off'):
                item = False
            else:
                item = True

        elif item_type == 'ms':
            item = Timing.string_to_ms(item)

        elif item_type == 'secs':
            item = Timing.string_to_secs(item)

        elif item_type == 'list_of_lists':
            item = Config.list_of_lists(item)

            # TODO

        elif item_type == 'ticks':
            item = Timing.string_to_ticks(item)

        return item

    def validate_item(self, item, validator, validation_failure_info):

        if '%' in validator and type(item) is str and item:

            if item is not None:

                try:
                    item = eval(validator.replace('%', "'" + item + "'"))
                except KeyError:
                    self.validation_error(item, validation_failure_info)

        elif validator in ('string', 'str'):
            if item is not None:
                item = str(item)
            else:
                item = None

        elif validator == 'float':
            item = float(item)

        elif validator == 'int':
            item = int(item)

        elif validator == 'bool':
            item = bool(item)

        return item

    def validation_error(self, item, validation_failure_info):
        self.log.error("Config validation error: Entry %s:%s:%s:%s is not valid",
                       validation_failure_info[0][0],
                       validation_failure_info[0][1],
                       validation_failure_info[1],
                       item)
        sys.exit()

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

        if source_int >= 0 and source_int <= 255:
            return format(source_int, 'x').upper().zfill(2)

        else:
            print "invalid source int:", source_int
            raise ValueError

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
