"""Perform hardware operations."""
import asyncio
import os
import random
import statistics
import time

from mpf.core.config_loader import YamlMultifileConfigLoader

from mpf.commands import MpfCommandLineParser

from mpf.core.machine import MachineController

SUBCOMMAND = True


class Command(MpfCommandLineParser):

    """Performs hardware operations."""

    def __init__(self, args, path):
        """Parse args."""
        command_name = args.pop(1)
        super().__init__(args=args, path=path)

        machine_path, remaining_args = self.parse_args()
        self.machine_path = machine_path
        self.args = remaining_args
        config_loader = YamlMultifileConfigLoader(machine_path, ["config.yaml"], True, False)

        config = config_loader.load_mpf_config()

        self.mpf = MachineController({"bcp": False,
                                      "no_load_cache": False,
                                      "mpfconfigfile": os.path.join(self.mpf_path, "mpfconfig.yaml"),
                                      "configfile": ["config"],
                                      "production": False,
                                      "create_config_cache": False,
                                      "force_platform": False,
                                      "text_ui": False
                                      }, config)

        method = getattr(self, command_name)
        method()

    def scan(self):
        """Scan hardware."""
        self.mpf.clock.loop.run_until_complete(self.mpf.initialise_core_and_hardware())
        if self.mpf.thread_stopper.is_set():
            raise AssertionError("Initialisation failed!")

        for name, platform in self.mpf.hardware_platforms.items():
            print("{}:".format(name))
            print(platform.get_info_string())
            print("---------")

        self.mpf.shutdown()

    def firmware_update(self):
        """Upgrade firmware of platforms."""
        self.mpf.clock.loop.run_until_complete(self.mpf.initialise_core_and_hardware())
        if self.mpf.thread_stopper.is_set():
            raise AssertionError("Initialisation failed!")

        for name, platform in self.mpf.hardware_platforms.items():
            print("{}:".format(name))
            print(platform.update_firmware())
            print("---------")

        self.mpf.shutdown()

    def _test_repeated_pulses_with_rule(self, config, pulse_ms, pause_min, pause_max):
        latency = []
        rule_latency = []
        pulse_duration = []
        rule_pulse_duration = []

        config["flipper"].enable()

        for _ in range(100):
            # measure coil -> input latency
            pulse_start = time.time()
            config["coil1"].pulse(pulse_ms=pulse_ms)

            self.mpf.clock.loop.run_until_complete(
                self.mpf.switch_controller.wait_for_switch(config["switch1"], state=1, only_on_change=False))
            switch_active = time.time()
            self.mpf.clock.loop.run_until_complete(
                self.mpf.switch_controller.wait_for_switch(config["switch2"], state=1, only_on_change=False))
            switch2_active = time.time()

            self.mpf.clock.loop.run_until_complete(
                self.mpf.switch_controller.wait_for_switch(config["switch1"], state=0, only_on_change=False))
            switch_inactive = time.time()
            self.mpf.clock.loop.run_until_complete(
                self.mpf.switch_controller.wait_for_switch(config["switch2"], state=0, only_on_change=False))
            switch2_inactive = time.time()

            self.mpf.clock.loop.run_until_complete(asyncio.sleep(random.uniform(pause_min * 0.001, pause_max * 0.001)))

            latency.append((switch_active - pulse_start) * 1000)
            rule_latency.append((switch2_active - switch_active) * 1000)
            pulse_duration.append((switch_inactive - switch_active) * 1000)
            rule_pulse_duration.append((switch2_inactive - switch2_active) * 1000)

        print("----------------------------------------------------------------------------------------")
        print("Pulse duration: {}ms Pause: {}ms to {}ms".format(pulse_ms, pause_min, pause_max))
        print("Latency mean: {:.2f} median: {:.2f} min: {:.2f} max: {:.2f} stdev: {:.2f} variance: {:.2f}".format(
            statistics.mean(latency), statistics.median(latency), min(latency), max(latency),
            statistics.stdev(latency), statistics.variance(latency)))
        print("Rule Latency mean: {:.2f} median: {:.2f} min: {:.2f} max: {:.2f} stdev: {:.2f} variance: {:.2f}".format(
            statistics.mean(rule_latency), statistics.median(rule_latency), min(rule_latency), max(rule_latency),
            statistics.stdev(rule_latency), statistics.variance(rule_latency)))
        print("Pulse duration measured mean: {:.2f} median: {:.2f} min: {:.2f} max: {:.2f} stdev: {:.2f} "
              "variance: {:.2f}".format(
                  statistics.mean(pulse_duration), statistics.median(pulse_duration), min(pulse_duration),
                  max(pulse_duration), statistics.stdev(pulse_duration), statistics.variance(pulse_duration)))
        print("Rule Pulse duration measured mean: {:.2f} median: {:.2f} min: {:.2f} max: {:.2f} stdev: {:.2f} "
              "variance: {:.2f}".format(
                  statistics.mean(rule_pulse_duration), statistics.median(rule_pulse_duration),
                  min(rule_pulse_duration), max(rule_pulse_duration), statistics.stdev(rule_pulse_duration),
                  statistics.variance(rule_pulse_duration)))
        print("----------------------------------------------------------------------------------------")
        print()

        config["flipper"].disable()

    def benchmark(self):
        """Benchmark hardware."""
        self.mpf.clock.loop.run_until_complete(self.mpf.initialise())
        if self.mpf.thread_stopper.is_set():
            raise AssertionError("Initialisation failed!")

        print(self.mpf.switches, self.mpf.coils)
        config = self.mpf.config_validator.validate_config("hardware_test", self.mpf.config.get("hardware_test", {}))
        print("1. Please confirm that you connected driver \"{}\" to switch \"{}\" and "
              "driver \"{}\" to switch \"{}\"".format(
                  config["coil1"], config["switch1"], config["coil2"], config["switch2"]))
        print("2. Turn off high voltage!")
        print("3. Hardware test will repeatedly pulse driver \"{}\" and \"{}\". "
              "Make sure they are not connected to coils and cannot cause any harm.".format(
                  config["coil1"], config["coil2"]))
        print("4. Turn off high voltage! (seriously)")
        print("")

        input_text = input("I am certain and know what I am doing (type YES if you are certain): ")
        if input_text != "YES":
            print("Wrong input. Exiting!")
            self.mpf.shutdown()
            return

        input_text = input("I did turn off high voltage (type HIGH VOLTAGE IS OFF): ")
        if input_text != "HIGH VOLTAGE IS OFF":
            print("Wrong input. Exiting!")
            self.mpf.shutdown()
            return

        print()
        print("This will take a few seconds. Please standby!")

        if config["flipper"].config["main_coil"] != config["coil2"]:
            print("Main_coil on flipper {} should be {} but is {}.".format(
                config["flipper"], config["coil2"], config["flipper"].config["main_coil"]))
            self.mpf.shutdown()
            return

        if config["flipper"].config["activation_switch"] != config["switch1"]:
            print("Activation_switch on flipper {} should be {} but is {}.".format(
                config["flipper"], config["switch1"], config["flipper"].config["activation_switch"]))
            self.mpf.shutdown()
            return

        if config["switch1"].state != 0:
            print("Switch {} should be inactive but is active.".format(config["switch1"]))
            self.mpf.shutdown()
            return

        if config["switch2"].state != 0:
            print("Switch {} should be inactive but is active.".format(config["switch2"]))
            self.mpf.shutdown()
            return

        # let the platform settle
        self.mpf.clock.loop.run_until_complete(asyncio.sleep(.5))

        self._test_repeated_pulses_with_rule(config, 53, 50, 100)
        self.mpf.clock.loop.run_until_complete(asyncio.sleep(.5))
        self._test_repeated_pulses_with_rule(config, 23, 5, 20)
        self.mpf.clock.loop.run_until_complete(asyncio.sleep(.5))
        self._test_repeated_pulses_with_rule(config, 13, 1, 2)

        self.mpf.shutdown()
