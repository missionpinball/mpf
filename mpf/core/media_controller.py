import asyncio

from grpc import aio

from mpf.core.mpf_controller import MpfController
from mpf.core.utility_functions import Util
from mpf.media_controller.server_pb2 import SlideAddRequest, WidgetAddRequest, ShowSlideRequest, SlideRemoveRequest
from mpf.media_controller.server_pb2_grpc import MediaControllerStub


class TempTarget:

    def __init__(self, name, rpc):
        self.slides = []
        self.name = name
        self.ready = True
        self.rpc = rpc

    def get_top_slide(self):
        if self.slides:
            return self.slides[0]

        return None

    async def add_slide(self, slide, transition_config):
        slide_add_request = SlideAddRequest()
        new_slide = await self.rpc.AddSlide(slide_add_request)
        slide.slide_id = new_slide.slide_id

        await slide.add_widgets(self.rpc)

        if self.slides and self.slides[0].priority < slide.priority:
            self.slides.insert(0, slide)
            await self.update_target(transition_config)

        elif not self.slides:
            self.slides.append(slide)
            await self.update_target(transition_config)
        else:
            self.slides.append(slide)

    async def replace_slide(self, old_slide, new_slide, transition_config):
        # TODO: only call update_target once here (and transition only once also)
        await self.remove_slide(old_slide, transition_config)
        await self.add_slide(new_slide, transition_config)

    async def remove_slide(self, slide, transition_config=None):
        print("YYY", self.slides, slide)
        self.slides.remove(slide)
        # TODO: this can be optimized by remembering if we need to sort
        self.slides = sorted(self.slides, key=lambda x: x.priority)
        # remove slide in MC
        slide_remove_request = SlideRemoveRequest()
        slide_remove_request.slide_id = slide.slide_id
        await self.rpc.RemoveSlide(slide_remove_request)
        await self.update_target(transition_config)

    async def update_target(self, transition_config=None):
        """Update top slide."""
        if not self.slides:
            return
        show_slide_request = ShowSlideRequest()
        show_slide_request.slide_id = self.slides[0].slide_id
        await self.rpc.ShowSlide(show_slide_request)


class TempSlide:

    def __init__(self, name, priority, slide_id):
        self.name = name
        self.slide_id = slide_id
        self.priority = priority
        self.widgets = []

    async def add_widgets(self, rpc):
        widget_add_request = WidgetAddRequest()
        widget_add_request.slide_id = self.slide_id
        widget_add_request.x = 5
        widget_add_request.y = 5
        widget_add_request.z = 2
        widget_add_request.rectangle_widget.color.red = 0.0
        widget_add_request.rectangle_widget.color.blue = 1.0
        widget_add_request.rectangle_widget.color.green = 0.5
        widget_add_request.rectangle_widget.color.alpha = 1.0
        widget_add_request.rectangle_widget.width = 500
        widget_add_request.rectangle_widget.height = 300
        await rpc.AddWidgetsToSlide(widget_add_request)


class MediaController(MpfController):

    config_name = "media_controller"

    def __init__(self, machine):
        super().__init__(machine)
        self.mc = None
        self.machine.events.add_async_handler('init_phase_2',
                                              self._load_slides)

        self.machine.targets = {}
        #self._next_slide_id = 0

    async def connect(self):
        """Connect to media controller."""
        channel = aio.insecure_channel('localhost:50051')
        rpc = MediaControllerStub(channel)
        self.machine.targets["default"] = TempTarget("default", rpc)

    # def get_next_slide_id(self):
    #     self._next_slide_id += 1
    #     return self._next_slide_id

    def create_slide(self, slide_name, priority):
        return TempSlide(slide_name, priority, None)

    async def _load_slides(self):
        await self.connect()
        slides = self.machine.config.get("slides", [])
        widgets = self.machine.config.get("widgets", [])
        print(slides, widgets)

        for mode in self.machine.modes.values():
            print(mode, mode.config.get("slides", []), mode.config.get("widgets", []))
