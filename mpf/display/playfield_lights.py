
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
