"""Util to copy light positions from monitor to MPF config."""
from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip

config_loader = YamlRoundtrip()
config_name = "config/leds.yaml"
monitor_config = config_loader.load("monitor/monitor.yaml")
lights_config = config_loader.load(config_name)

if "light" not in monitor_config:
    raise AssertionError("Monitor config does not contain a light section.")

if "lights" not in lights_config:
    raise AssertionError("Config does not contain a lights section.")

for light_name, light in lights_config['lights'].items():
    if light_name in monitor_config['light']:
        config = monitor_config['light'][light_name]
        x = config['x']
        y = config['y']

        lights_config['lights'][light_name]['x'] = x
        lights_config['lights'][light_name]['y'] = y

config_loader.save(config_name, lights_config)
