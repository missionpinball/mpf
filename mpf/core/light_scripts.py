from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util
from mpf.assets.show import Show


class LightScripts(object):

    def __init__(self, machine):
        self.machine = machine
        self.registered_light_scripts = CaseInsensitiveDict()

    def create_show_from_script(self, script, lights=None, leds=None,
                                light_tags=None, led_tags=None, key=None):
        """Creates a show from a script.

        Args:
            script: Python dictionary in MPF light script format
            lights: String or iterable of multiples strings of the matrix
            lights
                that will be included in this show.
            leds: String or iterable of multiples strings of the LEDs that will
                be included in this show.
            light_tags: String or iterable of multiples strings of tags of
                matrix lights that specify which lights will be in this show.
            led_tags: String or iterable of multiples strings of tags of
                LEDs that specify which lights will be in this show.
            key: Object (typically string) that will be used to stop the show
                created by this list later.

        """

        if type(script) is not list:
            script = Util.string_to_list(script)

        action_list = list()

        for step in script:

            this_step = dict()
            this_step['tocks'] = step['tocks']

            if lights and 'brightness' in this_step:
                this_step['lights'] = dict()

                for light in Util.string_to_list(lights):
                    this_step['lights'][light] = step['brightness']

            if light_tags and 'brightness' in this_step:
                if 'lights' not in this_step:
                    this_step['lights'] = dict()

                for tag in Util.string_to_lowercase_list(light_tags):
                    this_step['lights']['tag|' + tag] = step['brightness']

            if leds and 'color' in this_step:
                this_step['leds'] = dict()

                for led in Util.string_to_list(leds):
                    this_step['leds'][led] = RGBColor(step['color'])

            if led_tags and 'color' in this_step:
                if 'leds' not in this_step:
                    this_step['leds'] = dict()

                for tag in Util.string_to_lowercase_list(led_tags):
                    this_step['leds']['tag|' + tag] = RGBColor(step['color'])

            action_list.append(this_step)

        return Show(machine=self.machine, name='Script', file=None,
                    config=None, steps=action_list)

    def run_registered_light_script(self, script_name, **kwargs):

        return self.run_light_script(
            script=self.registered_light_scripts[script_name], **kwargs)

    def run_light_script(self, script, lights=None, leds=None, loops=-1,
                         callback=None, key=None, **kwargs):
        """Runs a light script.

        Args:
            script: A list of dictionaries of script commands. (See below)
            lights: A light name or list of lights this script will be applied
                to.
            leds: An LED name or a list of LEDs this script will be applied to.
            loops: The number of times the script loops/repeats (-1 =
            indefinitely).
            callback: A method that will be called when this script stops.
            key: A key that can be used to later stop the light show this
            script
                creates. Typically a unique string. If it's not passed, it will
                either be the first light name or the first LED name.
            **kwargs: Since this method just builds a Light Show, you can use
                any other Light Show attribute here as well, such as
                playback_rate, blend, repeat, loops, etc.

        Returns:
            :class:`Show` object. Since running a script just sets up and
            runs a regular Show, run_script returns the Show object.
            In most cases you won't need this, but it's nice if you want to
            know exactly which Show was created by this script so you can
            stop it later. (See the examples below for usage.)

        Light scripts are similar to Shows, except they only apply to single
        lights and you can "attach" any script to any light. Scripts are used
        anytime you want an light to have more than one action. A simple
        example
        would be a flash an light. You would make a script that turned it on
        (with your color), then off, repeating forever.

        Scripts could be more complex, like cycling through multiple colors,
        blinking out secret messages in Morse code, etc.

        Interally we actually just take a light script and dynamically convert
        it into a Show (that just happens to only be for a single light), so
        we can have all the other Show-like features, including playback
        speed, repeats, blends, callbacks, etc.

        The light script is a list of dictionaries, with each list item being a
        sequential instruction, and the dictionary defining what you want to
        do at that step. Dictionary items for each step are:

            color: The hex color for the led (ex: 00CC24)
            brightness: The hex brightness value for the light (ex: FF)
            time: How long (in ms) you want the light to be at that color
            fade_ms: True/False. Whether you want that light to fade to the
            color
                (using the *time* above), or whether you want it to switch to
                that color instantly.

        Example usage:

        Here's how you would use the script to flash an RGB light between red
        and off:

            self.flash_red = []
            self.flash_red.append({"color": 'ff0000', 'time': 1})
            self.flash_red.append({"color": '000000', 'time': 1})
            self.machine.show_controller.run_script(script=self.flash_red,
                                                    lights='light1',
                                                    priority=4,
                                                    blend=True)

        Once the "flash_red" script is defined as self.flash_red, you can use
        it anytime for any light or LED. You can also define lights as a list,
        like this:

            self.machine.show_controller.run_script(script=self.flash_red,
                                                    lights=['light1',
                                                    'light2'],
                                                    priority=4,
                                                    blend=True)

        Most likely you would define your scripts once when the game loads and
        then call them as needed.

        You can also make more complex scripts. For example, here's a script
        which smoothly cycles an RGB light through all colors of the rainbow:

            self.rainbow = []
            self.rainbow.append({'color': 'ff0000', 'time': 1, 'fade': True})
            self.rainbow.append({'color': 'ff7700', 'time': 1, 'fade': True})
            self.rainbow.append({'color': 'ffcc00', 'time': 1, 'fade': True})
            self.rainbow.append({'color': '00ff00', 'time': 1, 'fade': True})
            self.rainbow.append({'color': '0000ff', 'time': 1, 'fade': True})
            self.rainbow.append({'color': 'ff00ff', 'time': 1, 'fade': True})

        If you have single color lights, your *brightness* entries in your
        script
        would only contain a single hex value for the intensity of that light.
        For example, a script to flash a single-color light on-and-off (which
        you can apply to any light):

            self.flash = []
            self.flash.append({"brightness": "ff", "time": 1})
            self.flash.append({"brightness": "00", "time": 1})

        If you'd like to save a reference to the :class:`Show` that's
        created by this script, call it like this:

            self.blah = self.machine.show_controller.run_script("light2",
                                                        self.flash_red, "4",
                                                        playback_rate=2)
         """

        # convert the steps from the script list that was passed into the
        # format that's used in an Show

        show_actions = []

        if type(lights) is str:
            lights = [lights]

        if type(leds) is str:
            leds = [leds]

        if not key:
            try:
                key = lights[0]
            except (TypeError, IndexError):
                try:
                    key = leds[0]
                except (TypeError, IndexError):
                    return False

        for step in script:
            if step.get('fade', None):
                color = str(step['color']) + "-f" + str(step['time'])
            else:
                color = str(step['color'])

            current_action = {'time': step['time']}

            if lights:
                current_action['lights'] = dict()
                for light in Util.string_to_list(lights):
                    current_action['lights'][light] = color

            if leds:
                current_action['leds'] = dict()
                for led in Util.string_to_list(leds):
                    current_action['leds'][led] = color

            show_actions.append(current_action)

        show = Show(machine=self.machine, name='Script', file=None,
                    config=None, steps=show_actions)

        self.machine.show_controller.play_show(show=show, loops=loops,
                                               callback=callback, **kwargs)

        return show

    def stop_light_script(self, key, **kwargs):
        """Stops and removes the light show that was created by a light script.

        Args:
            key: The key that was specified in run_light_script().
            **kwargs: Not used, included in case this method is called via an
                event handler that might contain other random paramters.

        """

        try:
            self.stop_show(show=self.running_show_keys[key], **kwargs)
            del self.running_show_keys[key]
        except KeyError:
            pass
