"""Contains the Util class which includes many utility functions."""
from copy import deepcopy
import re
from fractions import Fraction
from functools import reduce

from typing import Dict, Iterable, List, Tuple, Callable, Any, Union
import asyncio
from ruamel.yaml.compat import ordereddict


class Util:

    """Utility functions for MPF."""

    hex_matcher = re.compile("(?:[a-fA-F0-9]{6,8})")

    # pylint: disable-msg=too-many-return-statements
    @staticmethod
    def convert_to_simply_type(value):
        """Convert value to a simple type."""
        # keep simple types
        if value is None:
            return None
        elif isinstance(value, (int, str, float)):
            return value

        # for list repeat per entry
        elif isinstance(value, list):
            return [Util.convert_to_simply_type(x) for x in value]

        elif isinstance(value, dict):
            new_dict = dict()
            for key, this_value in value.items():
                new_dict[Util.convert_to_simply_type(key)] = Util.convert_to_simply_type(this_value)

            return new_dict

        elif isinstance(value, tuple):
            # pylint: disable-msg=protected-access
            return tuple(Util.convert_to_simply_type(x) for x in value)

        # pylint: disable-msg=protected-access
        elif value.__class__.__name__ == "RGBColor":
            return value.rgb

        # otherwise just cast to string
        return str(value)

    @staticmethod
    def convert_to_type(value, type_name):
        """Convert value to type."""
        if type_name == "int":
            return int(value)
        elif type_name == "float":
            return float(value)
        elif type_name == "str":
            return str(value)
        else:
            raise AssertionError("Unknown type {}".format(type_name))

    @staticmethod
    def keys_to_lower(source_dict):
        """Convert the keys of a dictionary to lowercase.

        Args:
            source_dict: The dictionary you want to convert.

        Returns:
            A dictionary with lowercase keys.

        """
        if not source_dict:
            return dict()
        elif isinstance(source_dict, dict):
            for k in list(source_dict.keys()):
                if isinstance(source_dict[k], ordereddict):
                    # Dont know why but code will break with this specific dict
                    # TODO: fix this!
                    pass
                elif isinstance(source_dict[k], dict):
                    source_dict[k] = Util.keys_to_lower(source_dict[k])

            return dict((str(k).lower(), v) for k, v in source_dict.items())
        elif isinstance(source_dict, list):
            for num, item in enumerate(source_dict):
                source_dict[num] = Util.keys_to_lower(item)
            return source_dict
        else:
            raise AssertionError("Source dict has invalid format.")

    @staticmethod
    def string_to_list(string: Union[str, List[str], None]) -> List[str]:
        """Convert a comma-separated and/or space-separated string into a Python list.

        Args:
            string: The string you'd like to convert.

        Returns:
            A python list object containing whatever was between commas and/or
            spaces in the string.

        """
        if isinstance(string, str):
            if "{" in string:
                # Split the string on spaces/commas EXCEPT regions within braces
                new_list = re.findall(r'([\w|-]+?\{.*?\}|[\w|-]+)', string)
            else:
                # Convert commas to spaces, then split the string into a list
                new_list = string.replace(",", " ").split()
            # Look for string values of "None" and convert them to Nonetypes.
            for index, value in enumerate(new_list):
                if isinstance(value, str) and len(value) == 4 and value.lower() == 'none':
                    new_list[index] = None
            return new_list

        elif isinstance(string, list):
            return string  # If it's already a list, do nothing

        elif string is None:
            return []  # If it's None, make it into an empty list

        elif isinstance(string, (int, float)):
            return [string]

        elif str(type(string)) == "<class 'ruamel.yaml.comments.CommentedSeq'>":
            # If it's a ruamel CommentedSeq, just pretend its a list
            # I did it as a str comparison so I didn't have to
            # import the actual ruamel.yaml classes
            return string
        else:
            # if we're passed anything else raise an error
            raise AssertionError("Incorrect type in list for element {}".format(string))

    @staticmethod
    def string_to_lowercase_list(string: str) -> List[str]:
        """Convert a comma-separated and/or space-separated string into a Python list.

         Each item in the list has been converted to lowercase.

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
        """Convert an incoming string or list into a list of lists."""
        final_list = list()

        if isinstance(incoming_string, str):
            final_list = [Util.string_to_list(incoming_string)]

        else:
            for item in incoming_string:
                final_list.append(Util.string_to_list(item))

        return final_list

    @staticmethod
    def chunker(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @staticmethod
    def dict_merge(a, b, combine_lists=True):
        """Recursively merge dictionaries.

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
        # log.info("Dict Merge incoming A %s", a)
        # log.info("Dict Merge incoming B %s", b)
        if not isinstance(b, dict):
            return b
        result = deepcopy(a)
        for k, v in b.items():
            if v is None:
                continue
            if isinstance(v, dict) and '_overwrite' in v:
                result[k] = v
                del result[k]['_overwrite']
            elif isinstance(v, dict) and '_delete' in v:
                if k in result:
                    del result[k]
            elif k in result and isinstance(result[k], dict):
                result[k] = Util.dict_merge(result[k], v)
            elif k in result and isinstance(result[k], list):
                if isinstance(v, dict) and v[0] == dict(_overwrite=True):
                    result[k] = v[1:]
                elif isinstance(v, list) and combine_lists:
                    result[k].extend(v)
                else:
                    result[k] = deepcopy(v)
            else:
                result[k] = deepcopy(v)
        # log.info("Dict Merge result: %s", result)
        return result

    @staticmethod
    def hex_string_to_list(input_string, output_length=3):
        """Take a string input of hex numbers and return a list of integers.

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
        input_string = str(input_string).zfill(output_length * 2)

        for i in range(0, len(input_string), 2):  # step through every 2 chars
            output.append(int(input_string[i:i + 2], 16))

        return output[0:output_length:]

    @staticmethod
    def hex_string_to_int(inputstring: str, maxvalue: int = 255) -> int:
        """Take a string input of hex numbers and an integer.

        Args:
            inputstring: A string of incoming hex colors, like ffff00.
            maxvalue: Integer of the max value you'd like to return. Default is
                255. (This is the real value of why this method exists.)

        Returns:
            Integer representation of the hex string.

        """
        return_int = int(str(inputstring), 16)

        if return_int > maxvalue:
            return_int = maxvalue

        return return_int

    @staticmethod
    def event_config_to_dict(config):
        """Convert event config to a dict."""
        return_dict = dict()

        if isinstance(config, dict):
            return config
        elif isinstance(config, str):
            if config == "None":
                return {}
            config = Util.string_to_list(config)

        # 'if' instead of 'elif' to pick up just-converted str
        if isinstance(config, list):
            for event in config:
                return_dict[event] = 0

        return return_dict

    @staticmethod
    def int_to_hex_string(source_int: int) -> str:
        """Convert an int from 0-255 to a one-byte (2 chars) hex string, with uppercase characters."""
        source_int = int(source_int)

        if 0 <= source_int <= 255:
            return format(source_int, 'x').upper().zfill(2)

        else:
            raise ValueError("invalid source int: %s" % source_int)

    @staticmethod
    def pwm8_to_hex_string(source_int: int) -> str:
        """Convert an int to a PWM8 string."""
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
                             "0-8)" % source_int)

    @staticmethod
    def pwm32_to_hex_string(source_int: int) -> str:
        """Convert a PWM32 value to hex."""
        # generated by the int_to_pwm.py script in the mpf/tools folder

        lookup_table = {
            0: '00000000',  # 00000000000000000000000000000000
            1: '00000002',  # 00000000000000000000000000000010
            2: '00020002',  # 00000000000000100000000000000010
            3: '00400802',  # 00000000010000000000100000000010
            4: '02020202',  # 00000010000000100000001000000010
            5: '04102082',  # 00000100000100000010000010000010
            6: '08420842',  # 00001000010000100000100001000010
            7: '10884422',  # 00010000100010000100010000100010
            8: '22222222',  # 00100010001000100010001000100010
            9: '22448912',  # 00100010010001001000100100010010
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
                             "0-32)" % source_int)

    @staticmethod
    def pwm32_to_int(source_int: int) -> int:
        """Convert a PWM32 value to int."""
        # generated by the int_to_pwm.py script in the mpf/tools folder

        lookup_table = {
            0: 0,  # 00000000000000000000000000000000
            1: 2,  # 00000000000000000000000000000010
            2: 131074,  # 00000000000000100000000000000010
            3: 4196354,  # 00000000010000000000100000000010
            4: 33686018,  # 00000010000000100000001000000010
            5: 68165762,  # 00000100000100000010000010000010
            6: 138545218,  # 00001000010000100000100001000010
            7: 277365794,  # 00010000100010000100010000100010
            8: 572662306,  # 00100010001000100010001000100010
            9: 574916882,  # 00100010010001001000100100010010
            10: 613557394,  # 00100100100100100010010010010010
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
                             "0-32)" % source_int)

    @staticmethod
    def pwm8_to_int(source_int: int) -> int:
        """Convert a PWM8 value to int."""
        lookup_table = {
            0: 0,  # 00000000
            1: 1,  # 00000001
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
    def power_to_on_off(power: float, max_period: int = 20) -> Tuple[int, int]:
        """Convert a float value to on/off times."""
        if power > 1.0 or power < 0.0:
            raise ValueError("power has to be between 0 and 1")

        # special case for 0%
        if power == 0.0:
            return 0, 0

        fraction = Fraction.from_float(power).limit_denominator(max_period)

        on_ms = fraction.numerator
        off_ms = fraction.denominator - fraction.numerator

        return on_ms, off_ms

    @staticmethod
    def normalize_hex_string(source_hex: str, num_chars: int = 2) -> str:
        """Take an incoming hex value and convert it to uppercase and fills in leading zeros.

        Args:
            source_hex: Incoming source number. Can be any format.
            num_chars: Total number of characters that will be returned. Default
                is two.

        Returns:
            String, uppercase, zero padded to the num_chars.

        Example usage: Send "c" as source_hex, returns "0C".

        """
        if len(str(source_hex)) > num_chars:
            raise ValueError("Hex string is too long.")

        return str(source_hex).upper().zfill(num_chars)

    @staticmethod
    def bin_str_to_hex_str(source_int_str: str, num_chars: int) -> str:
        """Convert binary string to hex string."""
        return Util.normalize_hex_string('%0X' % int(source_int_str, 2),
                                         num_chars)

    @staticmethod
    def is_hex_string(string: str) -> bool:
        """Return true if string is hex."""
        return Util.hex_matcher.fullmatch(str(string)) is not None

    @staticmethod
    # pylint: disable-msg=too-many-return-statements
    def string_to_ms(time_string: str) -> int:
        """Decode a string of real-world time into an int of milliseconds.

        Example inputs:

        200ms
        2s
        None

        If no "s" or "ms" is provided, this method assumes "milliseconds."

        If time is 'None' or a string of 'None', this method returns 0.

        Returns:
            Integer. The examples listed above return 200, 2000 and 0,
            respectively
        """
        if time_string is None:
            return 0

        if isinstance(time_string, (int, float)):
            return int(time_string)

        time_string = str(time_string).upper()

        if time_string.endswith('MS') or time_string.endswith('MSEC'):
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(time_string)

        elif 'D' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 86400 * 1000)

        elif 'H' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 3600 * 1000)

        elif 'M' in time_string:
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 60 * 1000)

        elif time_string.endswith('S') or time_string.endswith('SEC'):
            time_string = ''.join(i for i in time_string if not i.isalpha())
            return int(float(time_string) * 1000)
        else:
            return int(time_string)

    @staticmethod
    def string_to_secs(time_string: str) -> float:
        """Decode a string of real-world time into an float of seconds.

        See 'string_to_ms' for a description of the time string.

        """
        time_string = str(time_string)

        if not any(c.isalpha() for c in time_string):
            time_string = ''.join((time_string, 's'))

        return Util.string_to_ms(time_string) / 1000.0

    @staticmethod
    def string_to_class(class_string: str) -> Callable[..., Any]:
        """Convert a string like mpf.core.events.EventManager into a Python class.

        Args:
            class_string(str): The input string

        Returns:
            A reference to the python class object

        This function came from here:
        http://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname

        """
        # todo I think there's a better way to do this in Python 3
        parts = class_string.split('.')
        module = ".".join(parts[:-1])
        m = __import__(module)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m

    @staticmethod
    def get_from_dict(dic, key_path):
        """Get a value from a nested dict (or dict-like object) from an iterable of key paths.

        Args:
            dic: Nested dict of dicts to get the value from.
            key_path: iterable of key paths

        Returns:
            value

        This code came from here:
        http://stackoverflow.com/questions/14692690/access-python-nested-dictionary-items-via-a-list-of-keys


        """
        try:
            res = reduce(lambda d, k: d[k], key_path, dic)
        except KeyError:
            return None

        return res

    @staticmethod
    def set_in_dict(dic, key_path, value):
        """Set a value in a nested dict-like object based on an iterable of nested keys.

        Args:
            dic: Nested dict of dicts to set the value in.
            key_path: Iterable of the path to the key of the value to set.
            value: Value to set.

        """
        Util.get_from_dict(dic, key_path[:-1])[key_path[-1]] = value

    @staticmethod
    def is_power2(num: int) -> bool:
        """Check a number to see if it's a power of two.

        Args:
            num: The number to check

        Returns: True or False

        """
        try:
            num = int(num)
        except (TypeError, ValueError):
            return False

        return num != 0 and ((num & (num - 1)) == 0)

    @staticmethod
    def db_to_gain(db: float) -> float:
        """Convert a value in decibels (-inf to 0.0) to a gain (0.0 to 1.0).

        Args:
            db: The decibel value (float) to convert to a gain

        Returns:
            Float
        """
        try:
            db = float(db)
        except (TypeError, ValueError):
            return 1.0

        return pow(10, db / 20.0)

    @staticmethod
    def string_to_gain(gain_string: str) -> float:
        """Convert string to gain.

        Decode a string containing either a gain value (0.0 to 1.0) or
        a decibel value (-inf to 0.0) into a gain value (0.0 to 1.0).

        Args:
            gain_string: The string to convert to a gain value

        Returns:
            Float containing a gain value (0.0 to 1.0)
        """
        gain_string = str(gain_string).lower()

        if gain_string.startswith('-inf'):
            return 0.0

        if gain_string.endswith('db'):
            gain_string = ''.join(i for i in gain_string if not i.isalpha())
            return min(max(Util.db_to_gain(float(gain_string)), 0.0), 1.0)

        try:
            return min(max(float(gain_string), 0.0), 1.0)
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def cancel_futures(futures: Iterable[asyncio.Future]):
        """Cancel futures."""
        for future in futures:
            if hasattr(future, "cancel"):
                future.cancel()

    @staticmethod
    def any(futures: Iterable[asyncio.Future], loop, timeout=None):
        """Return first future."""
        return Util.first(futures, loop, timeout, False)

    @staticmethod
    def ensure_future(coro_or_future, loop):
        """Wrap ensure_future."""
        if hasattr(asyncio, "ensure_future"):
            return asyncio.ensure_future(coro_or_future, loop=loop)
        else:
            # hack to support 3.4 and 3.7 at the same time
            _wrap_awaitable = getattr(asyncio, 'async')
            return _wrap_awaitable(coro_or_future, loop=loop)   # pylint: disable-msg=deprecated-method

    @staticmethod
    @asyncio.coroutine
    def first(futures: Iterable[asyncio.Future], loop, timeout=None, cancel_others=True):
        """Return first future and cancel others."""
        # wait for first
        try:
            done, pending = yield from asyncio.wait(iter(futures), loop=loop, timeout=timeout,
                                                    return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            Util.cancel_futures(futures)
            raise

        if cancel_others:
            # cancel all other futures
            for future in pending:
                future.cancel()

        if not done:
            raise asyncio.TimeoutError()
        # pylint: disable-msg=stop-iteration-return
        return next(iter(done))

    @staticmethod
    @asyncio.coroutine
    def race(futures: Dict[asyncio.Future, str], loop):
        """Return key of first future and cancel others."""
        # wait for first
        first = yield from Util.first(futures.keys(), loop=loop)
        return futures[first]

    @staticmethod
    def get_named_list_from_objects(switches) -> List[str]:
        """Return a list of names from a list of switch objects."""
        return [switch.name for switch in switches]
