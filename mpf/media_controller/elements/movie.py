"""Movie class which is a DisplayElement which plays MPEG-1 movies."""
# movie.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import pygame
import pygame.locals

from mpf.media_controller.core.display import DisplayElement
from mpf.media_controller.core.assets import Asset


class Movie(Asset):

    def _initialize_asset(self):

        self.movie_object = None

    def _load(self, callback):

        try:
            self.movie_object = pygame.movie.Movie(self.file_name)
        except pygame.error:
                self.asset_manager.log.error("Pygame Error for file %s. '%s'",
                                             self.file_name, pygame.get_error())
        except:
            raise Exception()

        self.movie_surface = pygame.Surface((self.movie_object.get_size()))
        self.movie_object.set_display(self.movie_surface)

        self.loaded = True

        if callback:
            callback()

    def _unload(self):
        self.movie_object = None


class MovieDisplayElement(DisplayElement):
    """Represents a movie display element.

    Args:
        slide: The Slide object this movie is being added to.
        machine: The main machine object.
        movie: The name of the registered movie element you'd like
            to play
        width: The width of the movie. A value of None means that it
            will play at its native width.
        height: The height of the movie. A value of None means that it
            will play at its native height.
        start_frame: Frame number (based on a 0-index) that this movie
            will start playing from.
        repeat: True/False for whether you want this movie to repeat
            when it's done. Default is True.
        play_now: True/False for whether this movie should start playing
            now. Default is True.
        x: The horizontal position offset for the placement of this element.
        y: The vertical position offset for the placement of this element.
        h_pos: The horizontal anchor.
        v_pos: The vertical anchor.

    Note: Full documentation on the use of the x, y, h_pos, and v_pos arguments
    can be found at: https://missionpinball.com/docs/displays/display-elements/positioning/

    """

    def __init__(self, slide, machine, movie, width=None, height=None,
                 start_frame=0, repeat=False, play_now=True, x=None, y=None,
                 h_pos=None, v_pos=None, layer=0, **kwargs):

        super(MovieDisplayElement, self).__init__(slide, x, y, h_pos, v_pos,
                                                  layer)

        self.loadable_asset = True
        self.machine = machine

        if movie not in machine.movies:
            self.log.critical("Received a request to add a movie, but "
                              "the name '%s' doesn't exist in in the list of "
                              "registered movies.", movie)
            raise Exception("Received a request to add a movie, but "
                              "the name '%s' doesn't exist in in the list of "
                              "registered movies.", movie)
        else:
            self.movie = machine.movies[movie]

        self.current_frame = start_frame
        self.repeat = repeat
        self.playing = play_now

        self.layer = layer

        if self.movie.loaded:
            self._asset_loaded()
        else:
            self.ready = False
            self.movie.load(callback=self._asset_loaded)

    def _asset_loaded(self):

        self.element_surface = self.movie.movie_surface
        self.set_position(self.x, self.y, self.h_pos, self.v_pos)
        self.ready = True

        if self.playing:
            self.play()

        super(MovieDisplayElement, self)._asset_loaded()

    def play(self, repeat=None):

        if repeat is not None:
            self.repeat = repeat
        elif repeat is True:
            self.repeat = -1

        self.movie.movie_object.play()

        self.playing = True
        self.dirty = True

    def update(self):
        if not self.playing:
            return

        self.dirty = True

        if not self.movie.movie_object.get_busy():
            self.restart()
            self.play()

        return True

    def stop(self):
        self.movie.movie_object.stop()
        self.playing = False

    def pause(self):
        self.movie.movie_object.pause()
        self.playing = False

    def advance(self, secs):
        self.movie.movie_object.skip(secs)

    def restart(self):
        self.movie.movie_object.rewind()

asset_class = Movie
asset_attribute = 'movies'  # self.machine.<asset_attribute>
display_element_class = MovieDisplayElement
create_asset_manager = True
path_string = 'movies'
config_section = 'Movies'
file_extensions = ('mpg', 'mpeg')
