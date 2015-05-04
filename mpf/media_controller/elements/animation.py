"""Animation class which is a DisplayElement which plays animations."""
# animation.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import time

from mpf.media_controller.core.display import DisplayElement
import mpf.media_controller.display_modules.dmd
from mpf.media_controller.core.assets import Asset

dmd_palette = [(0, 0, 0),
            (1, 0, 0),
            (2, 0, 0),
            (3, 0, 0),
            (4, 0, 0),
            (5, 0, 0),
            (6, 0, 0),
            (7, 0, 0),
            (8, 0, 0),
            (9, 0, 0),
            (10, 0, 0),
            (11, 0, 0),
            (12, 0, 0),
            (13, 0, 0),
            (14, 0, 0),
            (15, 0, 0)] * 16


class Animation(Asset):

    def _initialize_asset(self):

        if 'alpha_color' in self.config:
            self.alpha_color = (self.config['alpha_color'])
        else:
            self.alpha_color = None

        self.surface_list = None

    def _load(self, callback):

        # todo:
        # depth
        # w, h
        # load from image file

        if self.file_name.endswith('.dmd'):
            self.surface_list = mpf.media_controller.display_modules.dmd.load_dmd_file(
                self.file_name,
                dmd_palette,
                self.alpha_color)

        else:
            pass
            # add other animation formats

        # todo add the alpha

        self.loaded = True
        if callback:
            callback()

    def _unload(self):
        self.surface_list = None


class AnimationDisplayElement(DisplayElement):
    """Represents an animation display element.

    Args:
        slide: The Slide object this animation is being added to.
        machine: The main machine object.
        animation: The name of the registered animation element you'd like
            to play
        width: The width of the animation. A value of None means that it
            will play at its native width.
        height: The height of the animation. A value of None means that it
            will play at its native height.
        start_frame: Frame number (based on a 0-index) that this animation
            will start playing from.
        fps: How many frames per second this animation will play. Note that
            it's not possible to play animations faster that your machine HZ
            rate. Default is 10.
        repeat: True/False for whether you want this animation to repeat
            when it's done. Default is True.
        drop_frames: Whether this animation should drop (skip) any frames if
            it gets behind. True means that it will drop frames and skip ahead
            to whatever frame it should be at based on its fps. False means that
            it will always play the next frame, even if it's behind. Default is
            True.
        play_now: True/False for whether this animation should start playing
            now. Default is True.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at:
    https://missionpinball.com/docs/displays/display-elements/positioning/

    """

    def __init__(self, slide, machine, animation, width=None, height=None,
                 start_frame=0, fps=10, repeat=False, drop_frames=True,
                 play_now=True, x=None, y=None, h_pos=None,
                 v_pos=None, layer=0, **kwargs):

        super(AnimationDisplayElement, self).__init__(slide, x, y, h_pos, v_pos,
                                                      layer)

        self.loadable_asset = True
        self.machine = machine

        if animation not in machine.animations:
            raise Exception("Received a request to add an animation, but "
                            "the name registered animations.")
        else:
            self.animation = machine.animations[animation]

        self.current_frame = start_frame
        self.fps = 0
        self.repeat = repeat
        self.drop_frames = drop_frames
        self.playing = False
        self.secs_per_frame = 0
        self.next_frame_time = 0
        self.last_frame_time = 0
        self.set_fps(fps)
        self.layer = layer

        if self.animation.loaded:
            self._asset_loaded()
        else:
            self.ready = False
            self.animation.load(callback=self._asset_loaded)

        if play_now:
            self.play()
        # todo need to make it so that play() won't start until this all the
        # elements in this slide are ready to go

    def _asset_loaded(self):

        self.surface_list = self.animation.surface_list
        self.total_frames = len(self.surface_list)
        self.element_surface = self.surface_list[self.current_frame]
        self.set_position(self.x, self.y, self.h_pos, self.v_pos)
        self.ready = True

        super(AnimationDisplayElement, self)._asset_loaded()

    def set_fps(self, fps):
        """Sets the fps (frames per second) that this animation should play at.

        Args:
            fps: Integer value for how many fps you would like this animation to
                play at.

        If this animation is currently playing, this method will change the
        current playback rate.
        """
        self.fps = fps
        self.secs_per_frame = (1 / float(self.fps))
        self.next_frame_time = 0  # forces this to take place immediately

    def play(self, fps=None, start_frame=None, repeat=None):
        """Plays this animation.

        Args:
            fps: Sets the frames per second this animation should play at. If
                no value is passed, it will use whatever value was previously
                configured.
            start_frame: Sets the frame that you'd like this animation to start
                at. (The first frame in the animation is frame "0". If no value
                is passed, it will start at whatever frame it's currently set
                to.
            repeat: True/False for whether this animation should repeat when
                it reaches the end. If no value is passed, it will use whatever
                it's current repeat setting is.
        """
        if fps:
            self.set_fps(fps)
        if start_frame:
            self.current_frame = start_frame
        if type(repeat) is bool:
            self.repeat = repeat

        self.next_frame_time = 0
        self.playing = True
        self.dirty = True

    def stop(self, reset=False):
        """Stops this animation.

        Args:
            reset: True/False as to whether this animation should be reset to
            its first frame so it starts at the beginning the next time its
            played. Default is False.
        """

        if reset:
            self.current_frame = 0

        self.playing = False
        self.next_frame_time = 0

    def stop_when_done(self):
        """Tells this animation to stop (i.e. not to repeat) when it reaches its
        final frame. You can use this while an animation is playing to cause it
        to gracefully end when it hits the end rather than abrubtly stopping at
        its current frame."""
        self.repeat = False

    def jump_to_frame(self, frame, show_now=False):
        """Changes this animation to the frame you pass.

        Args:
            frame: Integer value of a frame number. (The first frame is "0").
            show_now: True/False as to whether this new frame should be shown
                immediately. A value of False means that this animation will
                start at this new frame the next time it's played.
        """
        self.current_frame = frame

        if show_now:
            self.show_frame()

    def jump(self, num_frames, show_now=False):
        """Jumps forward or backwards a given number of frames.

        Args:
            num_frames: An integer value of how many frames you'd like this
                animation to jump. A positive value jumps ahead, and a negative
                value jumps back. Note that if you pass a value that's greater
                than the total number of frames, the animation will "roll over"
                to the frame you passed. (For example, telling an animation with
                10 frames to jump 25 frames will make it end up on frame #5).
            show_now: True/False as to whether this new frame should be shown
                immediately. A value of False means that this animation will
                start at this new frame the next time it's played.
        """

        current_frame = self.current_frame
        current_frame += num_frames

        while current_frame > (self.total_frames - 1):
            if self.repeat:
                current_frame -= self.total_frames
            else:
                current_frame = self.total_frames - 1
                self.playing = False

        self.current_frame = current_frame

        if show_now:
            self.show_frame()

    def show_frame(self):
        """Forces the current frame of this animation to be shown on the
        display. (Behind the scenes, this method marks this animation as
        'dirty'). Note it might not actually be displayed based on whether the
        relative layer of this animation display element versus other display
        elements that may be active on this slide."
        """
        self.element_surface = self.surface_list[self.current_frame]
        self.dirty = True

    def update(self):
        """Internal method which updates this animation to whatever the current
        frame should be and marks this element as dirty so it will be picked up
        when the display is refreshed.
        """

        if not self.playing:
            return

        current_time = time.time()

        if not self.next_frame_time:
            # This animation is just starting up
            self.last_frame_time = current_time
            self.next_frame_time = current_time

        if self.next_frame_time <= current_time:  # need to show a frame
            # Figure out how many frames ahead we should be.
            # Look at how much time has passed since the last frame was
            # shown and divide that by secs_per_frame, then convert to int
            # so we just get the whole number part.
            num_frames = int((current_time - self.last_frame_time) /
                             self.secs_per_frame)

            self.last_frame_time = self.next_frame_time

            if num_frames > 1:  # we're behind

                if self.drop_frames:
                    # If we're dropping frames, then just set the next frame
                    # time to show when it ordinarily should. This will keep
                    # the playback speed consistent.

                    self.next_frame_time = current_time + self.secs_per_frame

                    #self.log.warning('Dropped %s frame(s)', num_frames-1)

                else:  # don't drop any frames
                    # If we're not dropping frames, we want to play them back
                    # as fast as possible to hopefully catch up, so we set the
                    # next frame time to the current time so we show another
                    # frame on the next loop.
                    self.next_frame_time = current_time

                    #self.log.warning('Animation is set to not drop frames, '
                    #                 'but is currently %s frame(s) behind',
                    #                 num_frames-1)

                    # Only advance 1 frame since we're not dropping any.
                    num_frames = 1

            else:  # we're on time
                self.next_frame_time = current_time + self.secs_per_frame

            self.jump(num_frames, show_now=True)

            self.decorate()
            return True

        if self.decorate():
            return True

        return False

asset_class = Animation
asset_attribute = 'animations'  # self.machine.<asset_attribute>
display_element_class = AnimationDisplayElement
create_asset_manager = True
path_string = 'animations'
config_section = 'animations'
file_extensions = ('dmd')


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
