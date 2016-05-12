import unittest
import ruamel.yaml as yaml
from ruamel.yaml.loader import RoundTripLoader
from mpf.file_interfaces.yaml_interface import YamlInterface


class TestYamlInterface(unittest.TestCase):

    def test_round_trip(self):

        orig_config = """\
hardware:
    platform: smart_virtual
    driverboards: virtual
    dmd: smartmatrix

config:
- portconfig.yaml
- switches.yaml
- coils.yaml
- devices.yaml
- keyboard.yaml
- virtual.yaml
- images.yaml

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
- base
- airlock_multiball

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
        parsed_config = YamlInterface.process(orig_config, True)
        saved_config = YamlInterface.save_to_str(parsed_config)

        # print(saved_config)

        self.assertEqual(orig_config, saved_config)

    def test_rename_key(self):
        yaml_str = '''

a: 1
b: 2
c: 3


'''
        data = yaml.load(yaml_str, Loader=RoundTripLoader)
        YamlInterface.rename_key('b', 'z', data)

        self.assertEqual(data['a'], 1)
        self.assertEqual(data['z'], 2)
        self.assertEqual(data['c'], 3)
