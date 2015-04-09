"""MPF Display Module which treats the playfield lights as a Pygame surface.
This module is not yet complete."""
# playfield_lights.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


import logging
import pygame
# todo make it so this doesn't crash if pygame is not available


class PlayfieldLights(object):

    def __init__(self, machine):
        self.machine = machine

        # create the pygame surface
        self.surface = pygame.Surface((205, 460))  # in tenths of inches
        self.surface.fill((0, 0, 0))

        self.machine.events.add_handler('timer_tick', self.tick)

    def update(self, surface):
        pa = pygame.PixelArray(surface)

        if hasattr(self.machine, 'lights'):  # todo got to be a better way
            for light in self.machine.lights:
                if light.x and light.y:
                    if pa[light.x, light.y]:
                        light.on()
                    else:
                        light.off()
        if hasattr(self.machine, 'leds'):
            for led in self.machine.leds:
                pass

    def tick(self):
        # see if the surface has changed, if so, update it todo
        self.update(self.surface)

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
