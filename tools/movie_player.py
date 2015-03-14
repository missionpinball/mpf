#!/usr/bin/env python

import sys
import os

if sys.platform == 'win32' and sys.getwindowsversion()[0] >= 5: # condi. and
    # On NT like Windows versions smpeg video needs windb.
    os.environ['SDL_VIDEODRIVER'] = 'windib'

import pygame
import pygame.movie
from pygame.locals import *


def main(filepath):
    pygame.init()
    pygame.mixer.quit()
    pygame.display.init()

    movie = pygame.movie.Movie(filepath)
    w, h = movie.get_size()
    #print w, h
    #w = int(w * 1.3 + 0.5)
    #h = int(h * 1.3 + 0.5)
    wsize = (w+10, h+10)
    msize = (w, h)
    screen = pygame.display.set_mode(wsize)
    movie.set_display(screen, Rect((5, 5), msize))

    pygame.event.set_allowed((QUIT, KEYDOWN))
    pygame.time.set_timer(USEREVENT, 1000)
    movie.play()
    while movie.get_busy():
        pygame.event.wait()

    if movie.get_busy():
        movie.stop()
    pygame.time.set_timer(USEREVENT, 0)

if __name__ == '__main__':
    main(sys.argv[1])
