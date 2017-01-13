import logging

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface


class Switch(SwitchPlatformInterface):
    def __init__(self, platform, config):
        self.log = logging.getLogger('Platform.DIYPinball.Switch')
        number = config['number']
        self.state = 0
        self.board, self.switch = [int(i) for i in number.split('-')]
        self.rules = {}
        super(Switch, self).__init__(config, number)

    def add_rule(self, rule):
        self.rules[rule.coil.number] = rule

    def remove_rule(self, coil):
        if coil.number in self.rules:
            self.rules.pop(coil.number)

    def process_event(self, event):
        for rule in self.rules.values():
            rule.process_event(event)
