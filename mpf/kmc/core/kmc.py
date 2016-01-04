

from kivy.graphics import InstructionGroup
from kivy.logger import Logger
from mpf.system.config import CaseInsensitiveDict

import time
import queue
from kivy.app import App

from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from mpf.kmc.core.bcp_processor import BcpProcessor
from mpf.kmc.core.mode_controller import ModeController
from mpf.system.events import EventManager
from mpf.system.config import Config as MpfConfig
from mpf.system.player import Player

from mpf.kmc.core.keyboard import MyKeyboardListener
from mpf.kmc.uix.screen_manager import ScreenManager as MpfScreenManager
from mpf.kmc.uix.mpf_display import MpfDisplay
from mpf.kmc.core import kivy_config_processor


class KmcApp(App):

    def __init__(self, options, config, machine_path, **kwargs):
        super(KmcApp, self).__init__(**kwargs)

        self.options = options

        self.machine_config = config
        self.machine_path = machine_path
        self.modes = CaseInsensitiveDict()
        self.player_list = list()
        self.player = None

        self.displays = dict()
        self.default_display = None

        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False

        self.events = EventManager(self, setup_event_player=False)
        self.config_processor = MpfConfig(self)

        print("---------")
        print(self.machine_config['screens'])
        print("---------")

        self.machine_config = kivy_config_processor.process_config(self.machine_config)

        print("+++++++++")
        print(self.machine_config['screens'])
        print("+++++++++")

        self.mode_controller = ModeController(self)
        self.screen_manager = MpfScreenManager(self)

        self.bcp_processor = BcpProcessor(self)

        self.setup_displays()

        self.events.post("init_phase_1")
        self.events._process_event_queue()
        self.events.post("init_phase_2")
        self.events._process_event_queue()
        self.events.post("init_phase_3")
        self.events._process_event_queue()
        self.events.post("init_phase_4")
        self.events._process_event_queue()
        self.events.post("init_phase_5")
        self.events._process_event_queue()

        self.reset()

    def get_config(self):
        return self.machine_config

    def setup_displays(self):
        # parse the displays: section of the config
        # if there is a window: section, then make sure there's a display with
        # the source_display name. If not, create it.

        # also parse the rest of the displays

        from kivy.core.window import Window

        w, h = 0, 0

        try:
            w, h = (self.machine_config['window']['width'],
                    self.machine_config['window']['height'])
        except KeyError:
            pass

        need_display = False
        if w and h:

            try:
                if (self.machine_config['window']['source_display'] not in
                        self.machine_config['displays']):
                    need_display = True
            except KeyError:
                need_display = True

        if need_display:
            self.create_display(width=Window.width, height=Window.height,
                                name='window', dpi=Window.dpi)

        try:
            for k, v in self.machine_config['displays'].items():
                self.create_display(width=v['width'],
                                    height=v['height'],
                                    name=k)
        except (AttributeError, TypeError):
            pass

        self.default_display = self.displays['window']


    def create_display(self, width, height, name, dpi=None, **kwargs):
        self.displays[name] = MpfDisplay(width=width, height=height)

        Clock.schedule_once(self.display_created)

    def display_created(self, *args, **kwargs):

        print('creating display post create', self.displays['window'].size)

    def build(self):

        self.crash_queue = queue.Queue()

        self.start_time = time.time()
        self.ticks = 0

        try:
            self.title = self.machine_config['window']['title']
        except KeyError:
            self.title = "Mission Pinball Framework"

        if 'keyboard' in self.machine_config:
            self.keyboard = MyKeyboardListener(self)

        if 'boot' in self.machine_config['screens']:
            new_screen = Screen(name='boot')

            for widget in self.machine_config['screens']['boot']:
                widget_obj = widget['widget_cls'](mc=self, **widget)
                widget_obj.x = 100
                widget_obj.y = 100
                # widget_obj.opacity = 0.5
                # widget_obj.pos_hint = {'top': 0.9}
                # widget_obj.size_hint
                widget_obj.font_name = 'Georgia'
                widget_obj.font_size = 30
                widget_obj.color = [1, 0, 0, 1]
                widget_obj.italic = True
                new_screen.add_widget(widget_obj)

            # new_screen.add_widget(Label(text='hello4', pos=(100, 100)))

            self.default_display.screen_manager.add_widget(new_screen)
            self.default_display.screen_manager.current = 'boot'

        return self.default_display

    def on_stop(self):
        print("loop rate", (self.ticks / (time.time() - self.start_time)))
        print("stopping...")
        self.bcp_processor.socket_thread.stop()

    def reset(self, **kwargs):
        print("reset")
        self.player = None
        self.player_list = list()

        self.events.add_handler('assets_to_load',
                                self._bcp_client_asset_loader_tick)

        # temp todo
        # self.events.replace_handler('timer_tick', self.asset_loading_counter)

        self.events.post('mc_reset_phase_1')
        self.events._process_event_queue()
        self.events.post('mc_reset_phase_2')
        self.events._process_event_queue()
        self.events.post('mc_reset_phase_3')
        self.events._process_event_queue()

    def game_start(self, **kargs):
        self.player = None
        self.player_list = list()
        self.num_players = 0
        self.events.post('game_started', **kargs)

        # self.screen_manager.transition = WipeTransition()
        # self.screen_manager.current = 'screen2'

        print(self.screen1.this_widget.text)
        self.screen1.this_widget.text = 'MOVING'
        print(self.screen1.this_widget.text)

        # self.show_screen('game_start')

    def game_end(self, **kwargs):
        self.player = None
        self.events.post('game_ended', **kwargs)

    def add_player(self, player_num):
        if player_num > len(self.player_list):
            new_player = Player(self, self.player_list)

            self.events.post('player_add_success', num=player_num)

    def update_player_var(self, name, value, player_num):
        try:
            self.player_list[int(player_num)-1][name] = value
        except (IndexError, KeyError):
            pass

    def player_start_turn(self, player_num):
        if ((self.player and self.player.number != player_num) or
                not self.player):

            try:
                self.player = self.player_list[int(player_num)-1]
            except IndexError:
                Logger.error('Received player turn start for player %s, but '
                               'only %s player(s) exist',
                               player_num, len(self.player_list))

    def _bcp_client_asset_loader_tick(self, total, remaining):
        self._pc_assets_to_load = int(remaining)
        self._pc_total_assets = int(total)

    # def asset_loading_counter(self):
    #
    #     if self.tick_num % 5 != 0:
    #         return
    #
    #     if AssetManager.total_assets or self._pc_total_assets:
    #         # max because this could go negative at first
    #         percent = max(0, int(float(AssetManager.total_assets -
    #                                    self._pc_assets_to_load -
    #                                    AssetManager.loader_queue.qsize()) /
    #                                    AssetManager.total_assets * 100))
    #     else:
    #         percent = 100
    #
    #     Logger.debug("Asset Loading Counter. PC remaining:{}, MC remaining:"
    #                    "{}, Percent Complete: {}".format(
    #                    self._pc_assets_to_load, AssetManager.loader_queue.qsize(),
    #                    percent))
    #
    #     self.events.post('asset_loader',
    #                      total=AssetManager.loader_queue.qsize() +
    #                            self._pc_assets_to_load,
    #                      pc=self._pc_assets_to_load,
    #                      mc=AssetManager.loader_queue.qsize(),
    #                      percent=percent)
    #
    #     if not AssetManager.loader_queue.qsize():
    #
    #     if True:
    #
    #         if not self.pc_connected:
    #             self.events.post("waiting_for_client_connection")
    #             self.events.remove_handler(self.asset_loading_counter)
    #
    #         elif not self._pc_assets_to_load:
    #             Logger.debug("Asset Loading Complete")
    #             self.events.post("asset_loading_complete")
    #             self.bcp_processor.send('reset_complete')
    #
    #             self.events.remove_handler(self.asset_loading_counter)

    def set_machine_var(self, name, value):
        try:
            prev_value = self.machine_vars[name]
        except KeyError:
            prev_value = None

        self.machine_vars[name] = value

        try:
            change = value-prev_value
        except TypeError:
            if prev_value != value:
                change = True
            else:
                change = False

        if change:
            Logger.debug("Setting machine_var '%s' to: %s, (prior: %s, "
                           "change: %s)", name, value, prev_value,
                           change)
            self.events.post('machine_var_' + name,
                                     value=value,
                                     prev_value=prev_value,
                                     change=change)

        if self.machine_var_monitor:
            for callback in self.monitors['machine_var']:
                callback(name=name, value=self.vars[name],
                         prev_value=prev_value, change=change)

    def show_screen(self, screen_name):

        list_settings = ['pos', 'color']
        cls_mappings = dict(label=Label)

        config = self.machine_config['screens'][screen_name]

        this_screen = Screen(name=screen_name)
        print("this_screen", this_screen)

        instruction_group = InstructionGroup()


        for widget in config:

            this_widget = Label(text='hello 2', color=(1,1,0,1), pos_hint={'x': 0, 'y': 0})
            # this_widget.color = (1,1,0,1)

            # for k in config[widget].keys():
            #
            #     if k in list_settings:
            #         config[widget][k] = Util.string_to_list(config[widget][k])
            #
            #
            # this_widget = cls_mappings[widget](**config[widget])
            #
            # print "this_widget", this_widget
            # print "kwargs", config[widget]

            this_screen.add_widget(this_widget)


        self.screen_manager.switch_to(this_screen)



class Screen1(Screen):

    def __init__(self, **kwargs):
        super(Screen1, self).__init__(**kwargs)

        self.name = 'screen1'

        widget = Label()
        # widget.bind(size=widget.setter('text_size'))

        widget.text_size = (800, 200)

        widget.text = 'Mission Pinball Framework'
        widget.bold = True
        widget.color = (1,1,0,1)
        # widget.pos=(10,10)
        widget.font_size = 50
        widget.halign = 'center'
        widget.valign = 'middle'

        self.add_widget(widget)

        self.this_widget = widget

class Screen2(Screen):

    def __init__(self, **kwargs):
        super(Screen2, self).__init__(**kwargs)

        self.name = 'screen2'

        self.add_widget(Label(text='Screen 2'))

        print(self, kwargs)

