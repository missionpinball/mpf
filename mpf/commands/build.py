"""Command to build artifacts for non-dev operations."""
import pickle

import argparse
from mpf.core.utility_functions import Util

from mpf.core.config_loader import YamlMultifileConfigLoader, ProductionConfigLoader

from mpf.commands import MpfCommandLineParser

SUBCOMMAND = True


class Command(MpfCommandLineParser):

    """Build artifacts."""

    def __init__(self, args, path):
        """Parse args."""
        command_name = args.pop(1)
        super().__init__(args=args, path=path)

        machine_path, remaining_args = self.parse_args()
        self.machine_path = machine_path
        self.args = remaining_args

        parser = argparse.ArgumentParser(
            description='Build MPF production config.')

        parser.add_argument("-c",
                            action="store", dest="configfile",
                            default="config.yaml", metavar='config_file',
                            help="The name of a config file to load. Default "
                                 "is "
                                 "config.yaml. Multiple files can be used "
                                 "via a comma-"
                                 "separated list (no spaces between)")

        parser.add_argument("-b",
                            action="store_false", dest="mc", default=True,
                            help="Builds a production config for MPF only, without MC.")

        parser.add_argument("--dest-path",
                            action="store", dest="dest_path", default=False,
                            help="Path to set as machine_path on the production bundle. May "
                                 "be different than the machine_path on the current machine.")

        self.args = parser.parse_args(remaining_args)
        self.args.configfile = Util.string_to_event_list(self.args.configfile)

        method = getattr(self, command_name)
        method()

    def production_bundle(self):
        """Create a production bundle."""
        config_loader = YamlMultifileConfigLoader(self.machine_path, self.args.configfile, False, False)

        mpf_config = config_loader.load_mpf_config()
        if self.args.dest_path:
            mpf_config.set_machine_path(self.args.dest_path)

        if self.args.mc:
            mc_config = config_loader.load_mc_config()
            if self.args.dest_path:
                mc_config.set_machine_path(self.args.dest_path)

        pickle.dump(mpf_config, open(ProductionConfigLoader.get_mpf_bundle_path(self.machine_path), "wb"))
        if self.args.mc:
            pickle.dump(mc_config, open(ProductionConfigLoader.get_mpf_mc_bundle_path(self.machine_path), "wb"))
        print("Success.")
