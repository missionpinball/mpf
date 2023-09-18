"""Command to start the MPF game engine."""

import argparse

from ruamel.yaml import YAML

from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.core.config_loader import YamlMultifileConfigLoader
from mpf.wire.fast import wire


class Command:

    """Runs the mpf game."""

    # pylint: disable-msg=too-many-locals,too-many-statements
    def __init__(self, mpf_path, machine_path, args):
        """Generate wiring for game from MPL file."""
        del mpf_path
        self.machine = None
        self._sigint_count = 0

        parser = argparse.ArgumentParser(description='Generates wiring .yaml file')

        parser.add_argument("-c",
                            action="store", dest="configfile",
                            default="config.yaml", metavar='config_file',
                            help="The name of a config file to load. Default "
                                 "is "
                                 "config.yaml. Multiple files can be used "
                                 "via a comma-"
                                 "separated list (no spaces between)")

        self.args = parser.parse_args(args)
        self.args.configfile = Util.string_to_event_list(self.args.configfile)

        # To initialize and check machine, load it onto the virtual platform - we have to use the virtual platform
        # because it would be helpful to be able to calculate wiring before setting up physical hardware.
        self.args.__dict__["production"] = False
        self.args.__dict__["force_platform"] = "smart_virtual"
        self.args.__dict__["text_ui"] = False
        self.args.__dict__["bcp"] = False

        config_loader = YamlMultifileConfigLoader(machine_path, self.args.configfile,
                                                  False, False)

        config = config_loader.load_mpf_config()

        # print(config.get_machine_config())

        self.machine = MachineController(vars(self.args), config)
        self.machine.initialize_mpf()

        result = wire(self.machine)

        yaml = YAML()
        yaml.default_flow_style = False
        f = open("wiring.yaml", "w", encoding="utf-8")
        yaml.dump(result, f)
        f.close()
