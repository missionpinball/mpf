"""Perform hardware operations."""
import os

from mpf.commands import MpfCommandLineParser

from mpf.core.machine import MachineController

subcommand = True


class Command(MpfCommandLineParser):

    """Performs hardware operations."""

    def __init__(self, args, path):
        """Parse args."""
        command_name = args.pop(1)
        super().__init__(args=args, path=path)

        machine_path, remaining_args = self.parse_args()
        self.machine_path = machine_path
        self.args = remaining_args
        self.mpf = MachineController(self.mpf_path, self.machine_path,
                                     {"bcp": False,
                                      "no_load_cache": False,
                                      "mpfconfigfile": os.path.join(self.mpf_path, "mpfconfig.yaml"),
                                      "configfile": ["config"],
                                      "production": False,
                                      "create_config_cache": False,
                                      "force_platform": False,
                                      "text_ui": False
                                      })
        self.mpf.clock.loop.run_until_complete(self.mpf.initialise_core_and_hardware())
        if self.mpf.thread_stopper.is_set():
            raise AssertionError("Initialisation failed!")

        method = getattr(self, command_name)
        method()

    def scan(self):
        """Scan hardware."""
        for name, platform in self.mpf.hardware_platforms.items():
            print("{}:".format(name))
            print(platform.get_info_string())
            print("---------")

        self.mpf.shutdown()

    def firmware_update(self):
        """Upgrade firmware of platforms."""
        for name, platform in self.mpf.hardware_platforms.items():
            print("{}:".format(name))
            print(platform.update_firmware())
            print("---------")

        self.mpf.shutdown()
