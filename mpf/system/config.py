import os

import yaml
from copy import deepcopy

class Config(object):

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
                `config['Config_path']`.)
            new_config_dict: A dictionary of settings to merge into the config
                dictionary.

        Note that you only need to specify a yaml_file or new_config_dictionary,
        not both.

        Returns: Python dictionary which is your source with all the new config
            options merged in.

        """

        if not config:
            config = dict()

        new_updates = dict()

        # If we were passed a config dict, load from there
        if type(new_config_dict) == dict:
            new_updates = new_config_dict

        # If not, do we have a yaml_file?
        elif yaml_file:
            if os.path.isfile(yaml_file):
                config_location = yaml_file
                # Pull out the path in case we need it later
                config['Config_path'] = os.path.split(yaml_file)[0]
            elif os.path.isfile(os.path.join(config['Config_path'],
                                             yaml_file)):
                config_location = os.path.join(config['Config_path'],
                                               yaml_file)
            else:
                #self.log.critical("Couldn't find config file: %s.", yaml_file)
                raise Exception("Couldn't find config file: %s.", yaml_file)

        if config_location:
            try:
                #self.log.info("Loading configuration from file: %s",
                #              config_location)
                new_updates = yaml.load(open(config_location, 'r'))
            except yaml.YAMLError, exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    #self.log.critical("Error found in config file %s. Line %s, "
                    #                  "Position %s", config_location,
                    #                  mark.line+1, mark.column+1)
                    raise Exception("Error found in config file %s. Line %s, "
                                    "Position %s", config_location,
                                    mark.line+1, mark.column+1)
            except:
                #self.log.critical("Couldn't load config from file: %s",
                #                  yaml_file)
                raise Exception("Couldn't load config from file: %s",
                                  yaml_file)

        config = Config.dict_merge(config, new_updates)

        # now check if there are any more updates to do.
        # iterate and remove them

        try:
            if 'Config' in config:
                if yaml_file in config['Config']:
                    config['Config'].remove(yaml_file)
                if config['Config']:
                    config = load_config_yaml(config=config,
                                              yaml_file=config['Config'][0])
        except:
            #self.log.critical("No configuration file found, or config file is "
            #                  "empty. But congrats! Your game works! :)")
            raise Exception("No configuration file found, or config file is "
                            "empty. But congrats! Your game works! :)")

        return config

    @staticmethod
    def process_config(config_spec, source_config):
        config_spec = yaml.load(config_spec)
        processed_config = dict()

        for k in config_spec.keys():

            print "checking", k

            if k in source_config:
                print "found it"
                processed_config[k] = Config.validate_config_item(
                    config_spec[k], source_config[k])
            else:
                print "couldn't find it"
                processed_config[k] = Config.validate_config_item(
                    config_spec[k], None)

            print
            print processed_config

        return processed_config

    @staticmethod
    def validate_config_item(spec, item):

        print "validate", spec, item

        if '|' in spec:
            item_type, default = spec.split('|')
        else:
            item_type = spec
            default = None

        if not item:
            item = default

        if item_type == 'list':
            return Config.string_to_list(item)
        elif item_type == 'int':
            return int(item)
        elif item_type == 'float':
            return float(item)
        elif item_type == 'string':
            return str(item)
        elif item_type == 'boolean':
            return bool(item)
        elif item_type == 'ms':
            return Timing.string_to_ms(item)

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
        return result

    @staticmethod
    def string_to_list(string):
        """ Converts a comma-separated and/or space-separated string into a
        python list.

        Args:
            string: The string you'd like to convert.

        Returns:
            A python list object containing whatever was between commas and/or
            spaces in the string.
        """
        if type(string) is str:
            return string.replace(',', ' ').split()
        elif type(string) is list:
            # if it's already a list, do nothing
            return string
        elif string is None:
            return []
        else:
            # if we're passed anything else, just make it into a list
            return [string]
