import unittest
import ruamel.yaml as yaml
from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip

from mpf.file_interfaces.yaml_interface import MpfLoader


class TestYamlInterface(unittest.TestCase):

    def test_round_trip(self):
        self.maxDiff = None

        orig_config = """\
hardware:
    platform: smart_virtual
    driverboards: virtual
    dmd: smartmatrix

config:
-   portconfig.yaml
-   switches.yaml
-   coils.yaml
-   devices.yaml
-   keyboard.yaml
-   virtual.yaml
-   images.yaml

dmd:
    physical: false
    width: 128
    height: 32
    type: color

window:
    elements:
    -   type: virtualdmd
        width: 512
        height: 128
        h_pos: center
        v_pos: center
        pixel_color: ff6600
        dark_color: 220000
        pixel_spacing: 1
    -   type: shape
        shape: box
        width: 516
        height: 132
        color: aaaaaa
        thickness: 2

modes:
-   base
-   airlock_multiball

sound_system:
    buffer: 512
    frequency: 44100
    channels: 1
    initial_volume: 1
    volume_steps: 20
    tracks:
        voice:
            volume: 1
            priority: 2
            simultaneous_sounds: 1
            preload: false
        sfx:
            volume: 1
            priority: 1
            preload: false
            simultaneous_sounds: 3
    stream:
        name: music
        priority: 0
"""
        parsed_config = YamlRoundtrip.process(orig_config)
        saved_config = YamlRoundtrip.save_to_str(parsed_config)

        # print(saved_config)

        self.assertEqual(orig_config, saved_config)

    def test_duplicate_key(self):
        yaml_str = '''

a: 1
b: 2
a: 3


'''
        with self.assertRaises(KeyError):
            yaml.load(yaml_str, Loader=MpfLoader)

    def test_yaml_patches(self):

        # tests our patches to the yaml processor

        config = """

str_1: +1
str_2: 032
str_3: on
str_4: off
str_5: 123e45
str_6: hi
str_7: 2:10
str_8: 2:10.1
bool_1: yes
bool_2: no
bool_3: true
bool_4: false
bool_5: True
bool_6: False
int_1: 123
yaml.scalarfloat.ScalarFloat_1: 1.0

        """

        values = {
            "str_1": "+1",
            "str_2": "032",
            "str_3": "on",
            "str_4": "off",
            "str_5": "123e45",
            "str_6": "hi",
            "str_7": "2:10",
            "str_8": "2:10.1",
            "bool_1": True,
            "bool_2": False,
            "bool_3": True,
            "bool_4": False,
            "bool_5": True,
            "bool_6": False,
            "int_1": 123,
            "yaml.scalarfloat.ScalarFloat_1": 1.0,
        }

        parsed_config = YamlRoundtrip.process(config)

        for k, v in parsed_config.items():
            if not type(v) is eval(k.split('_')[0]):
                raise AssertionError('YAML value "{}" is {}, not {}'.format(v,
                    type(v), eval(k.split('_')[0])))
            self.assertEqual(values[k], v)
