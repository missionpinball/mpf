"""Standalone Python tool which lets you preview TrueType fonts as they would be
rendered on a pinball DMD."""

# font_tester.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

"""
Requirements
------------

* Requires Python & Pygame. Any version of either should be fine?
* Works on Windows, Mac, Linux
* Does *not* require the Mission Pinball Framework. This tool is completely
  standalone.


Running the tool
----------------

Run this tool by specifying the path to a folder which has TrueType font files
(.ttf) you want to test. You can optionally specify a file name too which is the
first font it will load. Otherwise it just starts at the beginning of the
alphabet. For example:

python font_tester.py c:\Windows\Fonts

or

python font_tester.py ../mpf.fonts/pixelmix.ttf


Instructions
------------

Once the window pops up:

* Type any characters to have them appear in the window.
* Left & Right arrows cycle through the different fonts in the folder.
* Up & Down arrows increase & decrease the size of the font.
* Shift+Up & Shift+Down adjust the vertical placement of the font
* CTRL+A (or CMD+A on a Mac) toggles Antialias mode
* CTRL+B (or CMD+B) toggles the green Bounding Box.
* CTRL+S (or CMD+S) takes a snapshot of the screen and saves it to the
  'font_snapshots' folder

Limitations (which we will address soon):

* Only works with TrueType fonts with .ttf extensions.
* Doesn't work with shift symbols. (i.e. SHIFT+1 shows "1" and not "!")

"""

import os
import sys
from optparse import OptionParser

import pygame
import pygame.locals



# CONFIGURATION SETTINGS: You can change these if you want
# ------------------------------------------------------------------------------

window_size = (800, 600)                  # pixel size of the main window
dmd_size = (128, 32)                      # pixel size of the native DMD
dmd_screen_size = (640, 160)              # pixel size of the on screen DMD
pixel_color = (255, 85, 0)                # R, G, B colors of the font pixels
dark_color = (34, 17, 0)                  # R, G, B colors of the 'off' pixels
pixel_spacing = 2                         # Pixel spacing between dots
loop_ms = 100                             # How many ms it waits per cycle
font_bg_color = (0, 200, 0)               # R, G, B color of the CTRL+B box
max_chars = 20                            # How many characters are displayed
snapshot_folder = "font_snapshots"        # Path of the CTRL+S screenshots
prefer_uncompressed_snapshots = False     # Do you want uncompressed BMPs?
snapshot_flash_brightness = 255           # Color of the snapshot flash
snapshot_flash_steps = 5                  # Steps for the flash to be done

text_string = "HELLO"                     # Initial text
font_size = 10                            # Initial size
antialias = False                         # Initial antialias setting
bounding_box = False                      # Initial bounding box settings

# ------------------------------------------------------------------------------
# END OF CONFIGURATION SETTINGS. Don't change anything below here

font_path = None
font_list = list()
font_index = 0
char = None
y_offset = 0
snapshot_flash_index = 0

def load_font():
    global font
    global font_list
    global font_index
    global font_size
    global font_path

    font = pygame.font.Font(os.path.join(font_path, font_list[font_index]),
                            font_size)

def change_font_size(direction):
    global font_size

    if direction == 'up':
        font_size += 1
    elif direction == 'down' and font_size > 1:
        font_size -= 1

    load_font()
    update_screen()

def change_font(direction):
    global font_list
    global font_index

    if direction == 'left':
        font_index -= 1
    elif direction == 'right':
        font_index += 1

    if font_index < 0:
        font_index = len(font_list) - 1
    elif font_index > len(font_list) - 1:
        font_index = 0

    load_font()
    update_screen()

def change_y_offset(direction):
    global y_offset

    if direction == 'up':
        y_offset -= 1
    elif direction == 'down':
        y_offset += 1

def main_loop():
    global snapshot_flash_index
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            process_key(event.key, event.mod)

    pygame.time.delay(loop_ms)

    if snapshot_flash_index:
        snapshot_flash_index -= 1
        update_screen()

def process_key(key, mods):
    global text_string
    global max_chars
    ctrl = False
    shift = False

    # Calculate mods
    if (mods & pygame.locals.KMOD_SHIFT) or (mods & pygame.locals.KMOD_CAPS):
        shift = True

    if (mods & pygame.locals.KMOD_META) or (mods & pygame.locals.KMOD_CTRL):
        ctrl = True

    if key == pygame.locals.K_ESCAPE:
        sys.exit()

    else:
        char = pygame.key.name(key)

    if ctrl and char == 's':
        screen_snap()
    elif ctrl and char == 'a':
        flip_antialias()
    elif ctrl and char == 'b':
        flip_bounding_box()
    elif shift and (char == 'up' or char == 'down'):
        change_y_offset(char)
    elif char == 'up' or char == 'down':
        change_font_size(char)
    elif char == 'left' or char == 'right':
        change_font(char)
    else:
        text_string += get_char(char, shift)

    if len(text_string) > max_chars:
        text_string = text_string[-max_chars:]

    update_screen()

def update_screen():
    global font
    global antialias
    global text_string
    global pixel_color
    global dark_color
    global screen
    global dmd_size
    global dmd_screen_size
    global pixel_spacing
    global font_size
    global font_index
    global font_list
    global font_bg_color
    global bounding_box
    global snapshot_flash_index
    global snapshot_flash_brightness
    global snapshot_flash_steps
    global y_offset

    # render the text

    if bounding_box:
        text_surface = font.render(text_string, antialias, pixel_color,
                                   font_bg_color)
    else:
        text_surface = font.render(text_string, antialias, pixel_color)

    # figure out the x, y position to center this text in the DMD
    x = (dmd_size[0] - text_surface.get_width()) / 2
    y = ((dmd_size[1] - text_surface.get_height()) / 2) + y_offset

    # put that text on our 'DMD' surface in the way it will be in MPF

    dmd_surface = pygame.Surface((dmd_size))

    dmd_surface.fill(dark_color)

    dmd_surface.blit(text_surface, (x, y))

    # scale it
    dmd_screen_surface = pygame.transform.scale(dmd_surface, (dmd_screen_size))

    # pixelize it
    if pixel_spacing:

        ratio = dmd_screen_surface.get_width() / float(dmd_surface.get_width())

        for row in range(dmd_surface.get_height() + 1):
            pygame.draw.line(dmd_screen_surface, (0, 0, 0), (0, row*ratio),
                             (dmd_screen_surface.get_width()-1, row*ratio),
                             pixel_spacing)

        for col in range(dmd_surface.get_width() + 1):
            pygame.draw.line(dmd_screen_surface, (0, 0, 0), (col*ratio, 0),
                             (col*ratio, dmd_screen_surface.get_height()-1),
                             pixel_spacing)

    # Create the surface for the font name
    info_font = pygame.font.Font(None, 50)

    fontname_surface = info_font.render(font_list[font_index], True,
                                        (255, 255, 255))

    fontsize_surface = info_font.render("Font Size: " + str(font_size), True,
                                        (255, 255, 255))

    if antialias:
        aa_string = "ON"
    else:
        aa_string = "OFF"

    antialias_surface = info_font.render("Antialias: " + aa_string, True,
                                         (255, 255, 255))

    screen.fill((0,0,0))

    # center the DMD screen on the display surface
    x = (screen.get_width() - dmd_screen_surface.get_width()) / 2
    y = (screen.get_height() - dmd_screen_surface.get_height()) / 2

    # draw a box around the DMD
    pygame.draw.rect(screen, (255, 255, 255),
                     (x-1, y-1,dmd_screen_surface.get_width() + 2,
                      dmd_screen_surface.get_height() + 2), 1)

    screen.blit(dmd_screen_surface, (x, y))
    screen.blit(fontname_surface, (10,10))

    x = screen.get_width() - fontsize_surface.get_width() - 10

    screen.blit(fontsize_surface, (x, 10))

    y = screen.get_height() - antialias_surface.get_height() - 10

    screen.blit(antialias_surface, (10, y))

    if snapshot_flash_index:
        value = int(snapshot_flash_brightness * snapshot_flash_index /
                    float(snapshot_flash_steps))
        screen.fill((value, value, value))

    pygame.display.update()

def screen_snap():
    global snapshot_folder
    global font_list
    global font_index
    global font_size
    global antialias
    global prefer_uncompressed_snapshots
    global bounding_box
    global snapshot_flash_index
    global snapshot_flash_steps
    global y_offset

    # make sure we have our folder
    if not os.path.isdir(snapshot_folder):
        os.mkdir(snapshot_folder)

    surface = pygame.display.get_surface()
    filename = font_list[font_index].split('.')[0] + '-' + str(font_size)

    if antialias:
        filename += '-aa'

    if bounding_box:
        filename += '-bb'

    if y_offset:
        filename += '-y' + str(y_offset)

    if prefer_uncompressed_snapshots or not pygame.image.get_extended():
        filename += '.bmp'
    else:
        filename += '.png'

    filename = os.path.join(snapshot_folder, filename)

    pygame.image.save(surface, filename)

    snapshot_flash_index = snapshot_flash_steps

def flip_antialias():
    global antialias

    antialias ^= 1

def flip_bounding_box():
    global bounding_box

    bounding_box ^= 1

def get_char(char, shift):

    if char == 'space':
        return ' '

    if len(char) == 1:

        if char.isalpha() and shift:
            return char.upper()
        else:
            return char

    return ''

def setup_file_list(font_string):
    global font_file
    global font_path
    global font_list
    global font_index

    if os.path.isdir(font_string):
        font_path = font_string
        font_file = None

    elif os.path.isfile(font_string):
        font_path, font_file =  os.path.split(font_string)

    else:
        print "ERROR: Parameter passed isn't a valid path or file name."
        sys.exit()

    # Find all the fonts in this folder and add them to the list
    for item in os.walk(font_path):
        for file_name in item[2]:
            if file_name.upper().endswith('.TTF'):
                font_list.append(file_name)

    # figure out which one is ours
    if font_file:
        font_index = font_list.index(font_file)

def main():

    global screen

    # Get command line input
    parser = OptionParser()

    (options, args) = parser.parse_args()
    options = vars(options)

    if len(args) != 1:
        print "Error. This tool requires a font filename as a command line parameter"
        sys.exit()
    else:
        setup_file_list(args[0])

    pygame.init()

    # Set up the window

    flags = 0
    flags = flags | pygame.locals.RESIZABLE

    screen = pygame.display.set_mode(window_size, flags)

    pygame.display.set_caption("Mission Pinball Framework Font Tester")

    load_font()

    update_screen()

    while 1:
        main_loop()

if __name__ == "__main__":
    main()


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
