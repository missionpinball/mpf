from mpf.core.mpf_controller import MpfController


class ExampleController(MpfController):

    module_name = 'ExampleController'
    config_name = 'example_controller'

    def __init__(self, machine):
        super().__init__(machine)
        self.machine.validate_machine_config_section('example')
        greeting = self.machine.config['example']['greeting']
        self.info_log("ExampleController initialized: %s", greeting)
