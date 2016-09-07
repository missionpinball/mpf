import os
os.environ["KIVY_NO_ARGS"] = "1"

from queue import Queue

import time
from kivy import Config, Logger
from kivy.base import runTouchApp, EventLoop
from kivy.clock import Clock
from kivy.uix.widget import Widget

import mpfmc
from mpf.core.utility_functions import Util
from mpf.tests.MpfBcpTestCase import MockBcpClient
from mpf.tests.MpfTestCase import MpfTestCase
from mpfmc.core.config_processor import ConfigProcessor
from mpfmc.core.utils import load_machine_config


class TestBcpClient(MockBcpClient):
    def __init__(self, machine, name, bcp):
        super().__init__(machine, name, bcp)
        self.queue = Queue()
        self.exit_on_close = False

    def send(self, bcp_command, kwargs):
        self.queue.put((bcp_command, kwargs))

    def receive(self, bcp_command, callback=None, rawbytes=None, **kwargs):
        if rawbytes:
            kwargs['rawbytes'] = rawbytes
        self.receive_queue.put_nowait((bcp_command, kwargs))

        if callback:
            callback()


class MpfIntegrationTest(MpfTestCase):

    def get_options(self):
        return dict(machine_path=self.getAbsoluteMachinePath(),
                    mcconfigfile='mpfmc/mcconfig.yaml',
                    configfile=Util.string_to_list(self.getConfigFile()),
                    bcp=False)

    def preprocess_config(self, config):
        # TODO this method is copied from the mc.py launcher. Prob a better way
        kivy_config = config['kivy_config']

        try:
            kivy_config['graphics'].update(config['displays']['window'])
        except KeyError:
            pass

        try:
            kivy_config['graphics'].update(config['window'])
        except KeyError:
            pass

        if 'top' in kivy_config['graphics'] and 'left' in kivy_config['graphics']:
            kivy_config['graphics']['position'] = 'custom'

        for section, settings in kivy_config.items():
            for k, v in settings.items():
                try:
                    if k in Config[section]:
                        Config.set(section, k, v)
                except KeyError:
                    continue

    def _start_app_as_slave(self):
        # from app::run
        if not self.mc.built:
            self.mc.load_config()
            self.mc.load_kv(filename=self.mc.kv_file)
            root = self.mc.build()
            if root:
                self.mc.root = root
        if self.mc.root:
            if not isinstance(self.mc.root, Widget):
                Logger.critical('App.root must be an _instance_ of Widget')
                raise Exception('Invalid instance in App.root')
            from kivy.core.window import Window
            Window.add_widget(self.mc.root)

        # Check if the window is already created
        from kivy.base import EventLoop
        window = EventLoop.window
        if window:
            self.mc._app_window = window
            window.set_title(self.mc.get_application_name())
            icon = self.mc.get_application_icon()
            if icon:
                window.set_icon(icon)
            self.mc._install_settings_keys(window)
        else:
            Logger.critical("Application: No window is created."
                            " Terminating application run.")
            return

        self.mc.dispatch('on_start')
        runTouchApp(slave=True)  # change is here

        while not self.mc.is_init_done:
            EventLoop.idle()

    def _start_mc(self):
        from mpfmc.core.mc import MpfMc

        # prevent sleep in clock
        Clock._max_fps = 0

        mpf_config = ConfigProcessor.load_config_file(os.path.abspath(
            os.path.join(mpfmc.__path__[0], os.pardir,
                         self.get_options()['mcconfigfile'])), 'machine')

        machine_path = os.path.abspath(os.path.join(
            mpfmc.__path__[0], os.pardir, 'mpfmc', self.getAbsoluteMachinePath()))

        mpf_config = load_machine_config(
            Util.string_to_list(self.getConfigFile()),
            machine_path,
            mpf_config['mpf-mc']['paths']['config'], mpf_config)
        self.preprocess_config(mpf_config)

        self.mc = MpfMc(options=self.get_options(),
                        config=mpf_config,
                        machine_path=machine_path)

        from kivy.core.window import Window
        Window.create_window()
        Window.canvas.clear()

        self._start_app_as_slave()

    def _mc_time(self):
        return self._start_time + self.loop._time

    def _run_mc(self, dt):
        del dt
        Clock.time = self._mc_time
        if self.unittest_verbosity() > 1:
            time.sleep(.05)
        EventLoop.idle()

    def get_enable_plugins(self):
        return True

    def __init__(self, methodName):
        super().__init__(methodName)
        del self.machine_config_patches['mpf']['plugins']
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.integration.MpfIntegrationTest.TestBcpClient"}}}
        self.machine_config_patches['bcp']['servers'] = []

    def setUp(self):
        super().setUp()
        self._start_time = time.time()
        self._start_mc()
        self.clock.schedule_interval(self._run_mc, 1 / 30)

        client = self.machine.bcp.transport.get_named_client("local_display")
        bcp_mc = self.mc.bcp_processor
        bcp_mc.send = client.receive
        bcp_mc._client_connected()
        self.machine_run()
        while not client.queue.empty():
            bcp_mc.receive_queue.put(client.queue.get())
        client.queue = bcp_mc.receive_queue
        self.machine_run()

    def tearDown(self):
        self.mc.stop()
        EventLoop.close()
        super().tearDown()
        Clock._events = [[] for i in range(256)]
