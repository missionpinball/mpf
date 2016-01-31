"""Contains the Util class which includes many utility functions"""

from copy import deepcopy
from collections import OrderedDict
import re


class Util(object):

    hex_matcher = re.compile("(?:[a-fA-F0-9]{6,8})")

    @staticmethod
    def keys_to_lower(source_dict):
        """Converts the keys of a dictionary to lowercase.

        Args:
            source_dict: The dictionary you want to convert.

        Returns:
            A dictionary with lowercase keys.

        """
        if not source_dict:
            return dict()
        elif type(source_dict) in (dict, OrderedDict):
            for k in list(source_dict.keys()):
                if type(source_dict[k]) is dict:
                    source_dict[k] = Util.keys_to_lower(source_dict[k])

            return dict((str(k).lower(), v) for k, v in source_dict.items())
        elif type(source_dict) is list:
            for num, item in enumerate(source_dict):
                source_dict[num] = Util.keys_to_lower(item)
            return source_dict

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
        
        elif str(type(string)) == "<class 'ruamel.yaml.comments.CommentedSeq'>":
            return string  #If it's a ruamel CommentedSeq, just pretend its a list
                           #I did it as a str comparison so I didn't have to
                           #import the actual ruamel.yaml classes
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
        new_list = Util.string_to_list(string)

        new_list = [x.lower() for x in new_list]

        return new_list

    @staticmethod
    def list_of_lists(incoming_string):
        """ Converts an incoming string or list into a list of lists. """
        final_list = list()

        if type(incoming_string) is str:
            final_list = [Util.string_to_list(incoming_string)]

        else:
            for item in incoming_string:
                final_list.append(Util.string_to_list(item))

        return final_list

    @staticmethod
    def chunker(l, n):
        """Yields successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i+n]

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
        for k, v in b.items():
            if k in result and isinstance(result[k], dict):
                result[k] = Util.dict_merge(result[k], v)
            elif k in result and isinstance(result[k], list) and combine_lists:
                result[k].extend(v)
            else:
                result[k] = deepcopy(v)
        #log.info("Dict Merge result: %s", result)
        return result

    @staticmethod
    def hex_string_to_list(input_string, output_length=3):
        """Takes a string input of hex numbers and returns a list of integers.

        This always groups the hex string in twos, so an input of ffff00 will
        be returned as [255, 255, 0]

        Args:
            input_string: A string of incoming hex colors, like ffff00.
            output_length: Integer value of the number of items you'd like in
                your returned list. Default is 3. This method will ignore
                extra characters if the input_string is too long, and it will
                pad the left with zeros if the input string is too short.

        Returns:
            List of integers, like [255, 255, 0]

        Raises:
            ValueError if the input string contains non-hex chars

        """
        output = []
        input_string = str(input_string).zfill(output_length*2)

        for i in range(0, len(input_string), 2):  # step through every 2 chars
            output.append(int(input_string[i:i+2], 16))

        return output[0:output_length:]

    @staticmethod
    def hex_string_to_int(inputstring, maxvalue=255):
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
            config = Util.string_to_list(config)

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

    @staticmethod
    def bin_str_to_hex_str(source_int_str, num_chars):
        return Util.normalize_hex_string('%0X' % int(source_int_str, 2),
                                           num_chars)

    @staticmethod
    def is_hex_string(string):
        return Util.hex_matcher.fullmatch(str(string)) is not None