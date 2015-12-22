from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.video import Video
from kivy.graphics import (Rectangle, Triangle, Quad, Point, Mesh, Line,
                           BorderImage, Bezier, Ellipse)
from kivy.uix.image import Image
from mpf.kmc.widgets.text import Text
from kivy.utils import strtotuple, get_color_from_hex
from mpf.system.config import CaseInsensitiveDict

tuple_entries = ['pos', 'size']
color_entries = ['color']
type_map = CaseInsensitiveDict(text=Text,
                                image=Image,
                                video=Video,
                                bezier=Bezier,
                                border=BorderImage,
                                ellipse=Ellipse,
                                line=Line,
                                mesh=Mesh,
                                point=Point,
                                quad=Quad,
                                rectangle=Rectangle,
                                triangle=Triangle,
                                label=Label,
                                screen=Screen,
                                screen_manager=ScreenManager)

def process_config(config, mode=None):
    # config is a full MPF config dict
    if 'screens' in config:
        config['screens'] = process_screens(config['screens'], mode)

    return config

def process_screens(config, mode):
    # config is localized to 'screens' section
    for screen_name in config:
        config[screen_name] = process_screen(config[screen_name], mode)

    return config

def process_screen(config, mode):
    # config is localized to an single screen name entry
    if isinstance(config, dict):
        config = [config]

    else:
        config.reverse()

    for widget in config:
        widget = process_widget(widget, mode)

    return config

def process_widget(config, mode):
    # config is localized widget settings

    print(Text)
    print(config)
    print(type_map[config['type']])

    try:
        config['widget_cls'] = type_map[config['type']]
        del config['type']
    except KeyError:
        raise AssertionError('"{}" is not a valid MPF display widget type'
                             .format(config['type']))

    if not mode:
        priority = 0
    else:
        priority = mode.priority

    try:
        config['priority'] += priority
    except (KeyError, TypeError):
        config['priority'] = priority

    config['mode'] = mode

    for setting in config:
        if setting in tuple_entries:

            try:
                config[setting] = strtotuple(config[setting])
            except Exception:
                raise Exception('Error processing "{}: {}" from config file'
                                .format(setting, config[setting]))

        elif setting in color_entries:
            try:
                config[setting] = get_color_from_hex(str(config[setting]))
            except ValueError:
                raise ValueError('Error processing "{}: {}" from config file. '
                                 'Color values should be hex, like "ffaa00"'
                                 .format(setting, config[setting]))

    # validate_widget(config)

    return config

def validate_widget(config):
    config['widget_cls'](mc=None, **config)
    return