"""Contains the base class for virtual (image-based) score reels."""

from mpf.core.system_wide_device import SystemWideDevice


class VirtualScoreReel(SystemWideDevice):
  config_section = 'virtual_score_reels'
  collection = 'virtual_score_reels'
  class_label = 'virtual_score_reel'

  def __init__(self, machine, name):
    super().__init__(machine, name)
    self._frames = {}

  async def _initialize(self):
    await super()._initialize()
    self.machine.log.info("Initializing virtual score reel {}: {}".format(self.name, self.config))

    for frame in self.config["frames"]:
      self._frames[str(frame["character"])] = str(frame["frame"])

    self.machine.log.info("VSR created frames: {}".format(self._frames))
    self.machine.events.add_handler(self.name, self._post_reel_values)

  def _post_reel_values(self, **kwargs):
    names = ["1", "10", "100", "1k", "10k", "100k", "1m", "10m", "100m", "1b", "10b", "100b", "1t"]
    score = str(kwargs["value"])[::-1]
    result = { names[i]: self._frames[score[i]] for i in range(len(score))}
    self.machine.events.post("player{}_score_reel".format(self.machine.game.player.number), **result)