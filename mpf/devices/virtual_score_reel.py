"""Contains the base class for virtual (image-based) score reels."""

from mpf.core.system_wide_device import SystemWideDevice


class VirtualScoreReel(SystemWideDevice):
  config_section = 'virtual_score_reels'
  collection = 'virtual_score_reels'
  class_label = 'virtual_score_reel'

  def __init__(self, machine, name):
    super().__init__(machine, name)
    self._frames = {}
    self._reel_count = 0
    self._include_player_number = False

  async def _initialize(self):
    await super()._initialize()

    self._reel_count = self.config["reel_count"]
    self._include_player_number = self.config["include_player_number"]
    for frame in self.config["frames"]:
      self._frames[str(frame["character"])] = str(frame["frame"])

    self.machine.events.add_handler(self.name, self._post_reel_values)

  def _post_reel_values(self, **kwargs):
    # Virtual score reels support scores up to ten trillion
    names = ["1", "10", "100", "1k", "10k", "100k", "1m", "10m", "100m", "1b", "10b", "100b", "1t"]
    # Reverse the score and pad with zeroes up to the reel count
    score = str(kwargs["value"])[::-1].ljust(self._reel_count, "0")
    # Create a dict of reel name keys to target frame values
    result = { names[i]: self._frames[score[i]] for i in range(self._reel_count)}
    # Post the event
    event_name = "score_reel_{}_player{}".format(self.name, self.machine.game.player.number) if \
      self._include_player_number else "score_reel_{}".format(self.name)
    self.machine.events.post(event_name, **result)
