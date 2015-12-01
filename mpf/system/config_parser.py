



class ConfigParser(object):

    machine_wide_config = False
    mode_config = False
    config_section = ''

    def __init__(self, machine):
        self.machine = machine

