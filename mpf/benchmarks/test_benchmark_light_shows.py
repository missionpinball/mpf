import time

from functools import partial
from mpf.core.logging import LogMixin

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class BenchmarkLightShows(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'benchmarks/machine_files/shows/'

    def getOptions(self):
        options = super().getOptions()
        if self.unittest_verbosity() <= 1:
            options["production"] = True
        return options

    def get_platform(self):
        return 'virtual'

    def setUp(self):
        LogMixin.unit_test = False
        super().setUp()

    def _output(self, name, start, end, end2, num):
        print("Duration {} {:.5f}ms Processing {:.5f}ms Total: {:5f}ms Per second: {:2f}".format(
            name,
            (1000 * (end - start) / num), ((end2 - end) * 1000) / num, (1000 * (end2 - start)) / num,
            (num * 1) / (end2 - start)
        ))

    def _benchmark(self, function, name, num=10000, iterations=10):
        function(num, True)
        total = 0
        for i in range(iterations):
            start, end, end2 = function(num, False)
            total += (end2 - start) / num
            self._output(name, start, end, end2, num)

        print("Total average {:.5f}ms".format(total * 1000/ iterations))
        return total/iterations

    def testBenchmark(self):
        baseline = self._benchmark(partial(self._event_and_run, "random_event", "random_event2"), "baseline")
        minimal_show = self._benchmark(partial(self._event_and_run, "play_minimal_light_show", "stop_minimal_light_show"), "minimal_show")
        all_leds = self._benchmark(partial(self._event_and_run, "play_single_step_tag_playfield", "stop_single_step_tag_playfield"), "all_leds_tag")
        multi_step = self._benchmark(partial(self._event_and_run, "play_multi_step", "stop_multi_step"), "multi_step", num=500)

        print("Baseline: {:.5f}ms One LED: +{:.5f}ms 30 LEDs: +{:.5f}ms Multi Step: +{:.5f}".format(
            baseline * 1000,
            (minimal_show - baseline) * 1000,
            (all_leds - baseline) * 1000,
            (multi_step - baseline) * 1000
            ))

    def _event_and_run(self, event, event2, num, test):
        channel_list = []
        for light in self.machine.lights.values():
            for color, channels in light.hw_drivers.items():
                channel_list.extend(channels)

        start = time.time()
        for i in range(num):
            self.post_event(event)
            for channel in channel_list:
                brightness = channel.current_brightness
            self.advance_time_and_run(.01)
            for channel in channel_list:
                brightness = channel.current_brightness

        end = time.time()
        self.advance_time_and_run()
        end2 = time.time()
        self.post_event(event2)
        return start, end, end2
