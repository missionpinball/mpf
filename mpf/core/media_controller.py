from grpc import aio

from mpf.core.mpf_controller import MpfController
from mpf.media_controller.server_pb2 import SlideAddRequest, WidgetAddRequest, ShowSlideRequest, SlideRemoveRequest, \
    Widget
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

    async def _add_slide_to_remove_and_assign_id(self, slide):
        slide_add_request = SlideAddRequest()
        slide_add_request.widgets.extend(slide.get_widgets())
        new_slide = await self.rpc.AddSlide(slide_add_request)
        slide.slide_id = new_slide.slide_id
        return slide

    async def add_slide(self, slide, transition_config):
        slide = await self._add_slide_to_remove_and_assign_id(slide)
        if self.slides and self.slides[0].priority < slide.priority:
            self.slides.insert(0, slide)
            await self.update_target(transition_config)

        elif not self.slides:
            self.slides.append(slide)
            await self.update_target(transition_config)
        else:
            self.slides.append(slide)
            self.slides = sorted(self.slides, key=lambda x: x.priority)

    async def replace_slide(self, old_slide, new_slide, transition_config):
        needs_transition = False
        if self.slides[0] == old_slide or self.slides[0].priority < new_slide.priority:
            needs_transition = True

        await self._add_slide_to_remove_and_assign_id(new_slide)

        # replace element in place
        self.slides[self.slides.index(old_slide)] = new_slide
        # sort
        self.slides = sorted(self.slides, key=lambda x: x.priority)
        if needs_transition:
            await self.update_target(transition_config)

        await self._remove_slide_from_remote(old_slide)

    async def _remove_slide_from_remote(self, slide):
        slide_remove_request = SlideRemoveRequest()
        slide_remove_request.slide_id = slide.slide_id
        await self.rpc.RemoveSlide(slide_remove_request)

    async def remove_slide(self, slide, transition_config=None):
        has_been_top_slide = self.slides[0] == slide
        self.slides.remove(slide)
        if has_been_top_slide:
            # only transition if slide has been on top
            await self.update_target(transition_config)
        # remove slide in MC after triggering (potential) transition
        await self._remove_slide_from_remote(slide)

    async def update_target(self, transition_config=None):
        """Update top slide."""
        print("UPDATE", self.slides)
        if not self.slides:
            return
        show_slide_request = ShowSlideRequest()
        show_slide_request.slide_id = self.slides[0].slide_id
        await self.rpc.ShowSlide(show_slide_request)


class TempSlide:

    def __init__(self, name, priority, widgets):
        self.name = name
        self.slide_id = None
        self.priority = priority
        self._widgets = widgets

    def get_widgets(self):
        widgets = []
        widget = Widget()
        widget.x = 5
        widget.y = 5
        widget.z = 2
        widget.rectangle_widget.color.red = 0.0
        widget.rectangle_widget.color.blue = 1.0
        widget.rectangle_widget.color.green = 0.5
        widget.rectangle_widget.color.alpha = 1.0
        widget.rectangle_widget.width = 500
        widget.rectangle_widget.height = 300
        widgets.append(widget)
        return widgets

    async def add_widgets(self, rpc):
        widget_add_request = WidgetAddRequest()
        widget_add_request.slide_id = self.slide_id
        widget_add_request.widgets.extend(self.get_widgets())
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

    def parse_widgets(self, widget_config):
        widgets = []

        return widgets

    def create_slide(self, slide_name, widgets_config, priority):
        widgets = self.parse_widgets(widgets_config)
        return TempSlide(slide_name, priority, widgets)

    async def _load_slides(self):
        await self.connect()
        slides = self.machine.config.get("slides", [])
        widgets = self.machine.config.get("widgets", [])
        print(slides, widgets)

        for mode in self.machine.modes.values():
            print(mode, mode.config.get("slides", []), mode.config.get("widgets", []))
