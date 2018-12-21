"""Score queues for SS games."""
import asyncio
import math

from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice


class ScoreQueue(SystemWideDevice):

    """Score queues for SS games.

    Add scores over time and play a lot of chimes.
    """

    config_section = 'score_queues'
    collection = 'score_queues'
    class_label = 'score_queue'

    __slots__ = ["_score_queue", "_score_queue_empty", "_score_task"]

    def __init__(self, machine, name):
        """Initialise ball lock."""
        super().__init__(machine, name)
        self._score_queue = asyncio.Queue(loop=self.machine.clock.loop)
        self._score_queue_empty = asyncio.Event(loop=self.machine.clock.loop)
        self._score_queue_empty.set()
        self._score_task = None

        self.machine.events.add_async_handler("player_turn_ending", self._block_player_end_if_scoring)

    @asyncio.coroutine
    def _block_player_end_if_scoring(self, **kwargs):
        """Block player ending until scoring is done."""
        del kwargs
        yield from self._score_queue_empty.wait()

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        self._score_task = self.machine.clock.loop.create_task(self._handle_score_queue())
        self._score_task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def score(self, value, **kwargs):
        """Score a value via the queue."""
        del kwargs
        if not self.machine.game or not self.machine.game.player:
            self.warning_log("Trying to use score_queue without an active game or player")
            return
        self._score_queue_empty.clear()
        self._score_queue.put_nowait(value)

    def stop_device(self):
        """Stop queue."""
        if self._score_task:
            self._score_task.cancel()
            self._score_task = None

    @asyncio.coroutine
    def _handle_score_queue(self):
        while True:
            score = yield from self._score_queue.get()
            self.debug_log("Scoring %s", score)
            while score > 0:
                # get the position of the highest digit
                digit_pos = int(math.floor(math.log10(score)))
                digit_score = int(math.pow(10, digit_pos))
                # score this amount
                self.machine.game.player[self.name] += digit_score
                # reduce the remaining amount
                score -= digit_score
                self.debug_log("Scoring %s on digit %s. Remaining: %s", digit_score, digit_pos, score)
                # wait if there is a chime for that digit
                if len(self.config['chimes']) >= digit_pos and self.config['chimes'][-(digit_pos + 1)]:
                    self.config['chimes'][-(digit_pos + 1)].pulse()
                    self.debug_log("Played chime for pos %s. Waiting %ss", digit_pos, self.config['delay'])
                    yield from asyncio.sleep(self.config['delay'], loop=self.machine.clock.loop)

            if self._score_queue.empty():
                self._score_queue_empty.set()
