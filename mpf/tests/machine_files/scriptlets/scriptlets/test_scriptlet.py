from mpf.core.scriptlet import Scriptlet


class TestScriptlet(Scriptlet):
    def on_load(self):
        self.log.debug("Loaded!")

        self.machine.events.add_handler('test_event', self._update)

    def _update(self, **kwargs):
        del kwargs
        self.machine.events.post("test_response")