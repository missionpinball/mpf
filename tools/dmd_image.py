# dmd_image.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


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
pixel_color = [255, 85, 0]                # R, G, B colors of the image pixels
dark_color = [0, 0, 0]                  # R, G, B colors of the 'off' pixels
pixel_spacing = 2                         # Pixel spacing between dots
loop_ms = 100                             # How many ms it waits per cycle
file_extensions = ['bmp', 'jpg', 'jpeg', 'gif', 'png', 'tif']

shades = 16
alpha_color = None
red = 299           # .299
green = 587        # .587
blue = 114         # .114


# ------------------------------------------------------------------------------
# END OF CONFIGURATION SETTINGS. Don't change anything below here

image_path = None
image_list = list()
image_index = 0
x_offset = 0
y_offset = 0
snapshot_flash_index = 0
dmd_palette = None

source_image_dmd_surface = None
source_image_screen_surface = None
source_image_surface = None

def load_image():
    global source_image_surface
    global image_list
    global image_index
    global image_size
    global image_path

    source_image_surface = pygame.image.load(os.path.join(image_path,
                                                        image_list[image_index]))


def change_image(direction):
    global image_list
    global image_index

    if direction == 'left':
        image_index -= 1
    elif direction == 'right':
        image_index += 1

    if image_index < 0:
        image_index = len(image_list) - 1
    elif image_index > len(image_list) - 1:
        image_index = 0

    load_image()
    update_screen()

def change_offset(direction):
    global y_offset
    global x_offset

    if direction == 'up':
        y_offset -= 1
    elif direction == 'down':
        y_offset += 1
    elif direction == 'left':
        x_offset -= 1
    elif direction == 'right':
        x_offset += 1

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
    elif shift and (char == 'up' or char == 'down' or
                    char == 'left' or char == 'right'):
        change_offset(char)
    elif char == 'up' or char == 'down':
        change_image_size(char)
    elif char == 'left' or char == 'right':
        change_image(char)
    else:
        #text_string += get_char(char, shift)
        pass

    update_screen()

def update_screen():
    global source_image_surface
    #global source_image_screen_surface
    global pixel_color
    global dark_color
    global screen
    global dmd_size
    global dmd_screen_size
    global pixel_spacing
    global image_index
    global image_list
    global image_bg_color
    global snapshot_flash_index
    global snapshot_flash_brightness
    global snapshot_flash_steps
    global y_offset
    global x_offset
    global dmd_palette

    new_image_dmd_surface = pygame.Surface((dmd_size), depth=8)
    new_image_dmd_surface.set_palette(dmd_palette)
    new_image_dmd_surface.fill(dark_color)

    new_image_dmd_surface.blit(surface_to_dmd(source_image_surface),
                                              (x_offset, y_offset))

    source_image_dmd_surface = pygame.Surface((dmd_size))
    source_image_dmd_surface.fill(dark_color)
    source_image_dmd_surface.blit(source_image_surface, (x_offset, y_offset))

    source_image_screen_surface = make_screen_surface(source_image_dmd_surface,
                                                      dmd_screen_size, pixel_spacing)
    new_image_screen_surface = make_screen_surface(new_image_dmd_surface,
                                                   dmd_screen_size, pixel_spacing)

    # Create the surface for the image name
    info_image = pygame.font.Font(None, 50)

    imagename_surface = info_image.render(image_list[image_index], True,
                                        (255, 255, 255))

    screen.fill((0,0,0))

    # center the DMD screen on the display surface
    x = (screen.get_width() - source_image_screen_surface.get_width()) / 2
    y = (screen.get_height() - source_image_screen_surface.get_height()) / 3

    # draw a box around the source DMD
    pygame.draw.rect(screen, (255, 255, 255),
                     (x-1, 100-1, source_image_screen_surface.get_width() + 2,
                      source_image_screen_surface.get_height() + 2), 1)

    # draw a box around the new DMD
    pygame.draw.rect(screen, (255, 255, 255),
                     (x-1, 400-1, source_image_screen_surface.get_width() + 2,
                      source_image_screen_surface.get_height() + 2), 1)


    screen.blit(source_image_screen_surface, (x, 100))
    screen.blit(new_image_screen_surface, (x, 400))

    screen.blit(imagename_surface, (10,10))

    if snapshot_flash_index:
        value = int(snapshot_flash_brightness * snapshot_flash_index /
                    float(snapshot_flash_steps))
        screen.fill((value, value, value))

    pygame.display.update()


def make_screen_surface(surface, dimensions, pixel_spacing=0):

    # scale it
    new_surface = pygame.transform.scale(surface, (dimensions))

    # pixelize it
    if pixel_spacing:

        ratio = new_surface.get_width() / float(surface.get_width())

        for row in range(surface.get_height() + 1):
            pygame.draw.line(new_surface, (0, 0, 0), (0, row*ratio),
                             (new_surface.get_width()-1, row*ratio),
                             pixel_spacing)

        for col in range(surface.get_width() + 1):
            pygame.draw.line(new_surface, (0, 0, 0), (col*ratio, 0),
                             (col*ratio, new_surface.get_height()-1),
                             pixel_spacing)

    return new_surface


def surface_to_dmd(surface):

    global dmd_palette
    global shades
    global red
    global green
    global blue
    global alpha_color

    total_weights = float(red + blue + green)
    red_mult = red / total_weights
    green_mult = green / total_weights
    blue_mult = blue / total_weights

    width, height = surface.get_size()
    pa = pygame.PixelArray(surface)
    new_surface = pygame.Surface((width, height), depth=8)

    # todo add support for alpha channel (per pixel), and specifying the
    # alpha color before the conversion versus after

    new_surface.set_palette(dmd_palette)

    if alpha_color is not None:
        new_surface.set_colorkey((alpha_color, 0, 0))

    new_pa = pygame.PixelArray(new_surface)

    for x in range(width):
        for y in range(height):
            pixel_color = surface.unmap_rgb(pa[x, y])
            pixel_weight = ((pixel_color[0] * red_mult) +
                            (pixel_color[1] * green_mult) +
                            (pixel_color[2] * blue_mult)) / 255.0

            new_pa[x, y] = int(round(pixel_weight * (shades - 1)))

            '''
            if new_pa[x, y] > shades -1:
                print "max shade", shades-1
                print "this shade", new_pa[x, y]
                print "source pixel", pixel_color
                print "mults", red_mult, green_mult, blue_mult
                print "calculated weight", pixel_weight
                print "caluculated ratio", pixel_weight / 255.0
                print "calculated value", pixel_weight / 255.0 * shades
                print "rounded", round(pixel_weight / 255.0 * shades)
                sys.exit()
            '''

    return new_pa.surface

def create_palette():
    global shades
    global dark_color
    global pixel_color
    global dmd_palette

    palette = []
    step_size = [(pixel_color[0] - dark_color[0]) / (shades - 1.0),
                 (pixel_color[1] - dark_color[1]) / (shades - 1.0),
                 (pixel_color[2] - dark_color[2]) / (shades - 1.0)
                 ]

    current_color = dark_color

    # manually add the first entry to ensure it's exactly as entered
    palette.append((int(current_color[0]),
                    int(current_color[1]),
                    int(current_color[2])))

    # calculate all the middle values (all except the dark and bright)
    for i in range(shades-2):
        current_color[0] += step_size[0]
        current_color[1] += step_size[1]
        current_color[2] += step_size[2]
        palette.append((int(current_color[0]),
                        int(current_color[1]),
                        int(current_color[2])))

    # manually add the last entry to ensure it's exactly as entered
    palette.append(pixel_color)

    dmd_palette = palette

def screen_snap():
    global snapshot_folder
    global image_list
    global image_index
    global image_size
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
    filename = image_list[image_index].split('.')[0] + '-' + str(image_size)

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

def setup_file_list(image_string):
    global image_file
    global image_path
    global image_list
    global image_index

    if os.path.isdir(image_string):
        image_path = image_string
        image_file = None

    elif os.path.isfile(image_string):
        image_path, image_file =  os.path.split(image_string)

    else:
        print "ERROR: Parameter passed isn't a valid path or file name."
        sys.exit()

    # Find all the images in this folder and add them to the list
    for item in os.walk(image_path):
        for file_name in item[2]:
            if file_name.upper().endswith('.BMP'):
                image_list.append(file_name)

    # figure out which one is ours
    if image_file:
        image_index = image_list.index(image_file)

def main():

    global screen
    global dmd_palette
    global pixel_color
    global dark_color
    global shades

    # Get command line input
    parser = OptionParser()

    (options, args) = parser.parse_args()
    options = vars(options)

    if len(args) != 1:
        print "Error. This tool requires a image filename as a command line parameter"
        sys.exit()
    else:
        setup_file_list(args[0])

    pygame.init()

    # Set up the window

    flags = 0
    flags = flags | pygame.locals.RESIZABLE

    screen = pygame.display.set_mode(window_size, flags)

    pygame.display.set_caption("Mission Pinball Framework Image Tester")


    create_palette()

    load_image()

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
