import logging
import sys
from mpf.core.config_loader import YamlMultifileConfigLoader

from mpf.core.machine import MachineController

machine_path = sys.argv[1]

config_loader = YamlMultifileConfigLoader(machine_path, ["config.yaml"], False, False)
config = config_loader.load_mpf_config()

options = {
    'force_platform': 'smart_virtual',
    'production': False,
    'mpfconfigfile': ["mpfconfig.yaml"],
    'configfile': ["config.yaml"],
    'debug': True,
    'bcp': True,
    'no_load_cache': False,
    'create_config_cache': True,
    'text_ui': False,
    'consoleloglevel': logging.DEBUG,
}
logging.basicConfig(level=logging.DEBUG)
machine = MachineController(options, config)
machine.run()
