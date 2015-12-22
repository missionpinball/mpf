

class ScreenManager(object):

    def __init__(self, mc):
        self.mc = mc

        # self.mc.mode_controller.register_load_method(self.validate_screens,
        #                                              'screens')


    def validate_screens(self, config, mode_path, **kwargs):

        for screen_name in list(config.keys()):

            for widget in config[screen_name]:

                spec = 'screens:{}'.format(widget['type'])

                processed = self.validate_screen(spec, widget)

        quit()


            # print config[screen_name]
            #
            # processed = self.validate_screen(screen_name, config[screen_name])
            #
            # if processed:
            #     config[screen_name] = processed
            #
            # else:
            #     del config[screen_name]
            #     print "error processing screen", screen_name
            #     quit()

    def validate_screen(self, spec, config):



        return self.mc.config_processor.process_config2(spec, config)