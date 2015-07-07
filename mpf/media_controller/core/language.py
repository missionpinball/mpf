"""Contains the parent class for MPF's Language module."""
# language.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import re

from mpf.system.config import Config

class Language(object):
    """MPF module which handles text, audio, and video replacement of objects
    for multi-language environments.

    Args:
        machine: The main machine object

    """

    def __init__(self, machine):

        self.log = logging.getLogger('Language')
        self.machine = machine
        self.config = None
        self.machine.language = None
        self.current_language = None

        # See if there's a Languages section in the config and it's not empty
        if 'languages' in self.machine.config and (
                self.machine.config['languages']):
            self._configure()

    def _configure(self):
        self.config = self.machine.config['languages']
        self.machine.language = self
        self.languages = Config.string_to_lowercase_list(
            self.machine.config['languages'])

        # Set the default language to the first entry in the list
        self.set_language(self.languages[0])
        self.default_language = self.languages[0]

        self.find_text = re.compile('(\(.*?\))')

    def set_language(self, language_string):
        """Sets the current language based on the string passed.

        Args:
            language_string: The string name of the language you want to set the
                machine to.

        Language strings can be whatever you want, based on how you define them
        in your config file. It can be an actual language, like English or
        French, or it can simply be alternate assets, like "Kid-Friendly" versus
        "Mature."

        This language change is instant, and you can safely call it often.
        Change languages for each player in the same game, or even in the middle
        of a ball!

        """

        self.log.debug('Setting language to: %s', language_string)
        self.current_language = language_string

    def get_language(self):
        """Returns the string name of the current language."""
        return self.current_language

    def text(self, text):
        """Translates a text string (or part of a text string) based on the
        current language setting.

        Args:
            text: The string of text you want to translate.

        Returns: A translated string.

        The incoming text string is searched for text within parentheses, and
        each of those segments is looked up for replacement. You can wrap the
        entire string in parentheses, or just part of it, or multiple parts.

        A new, translated string is returned with the parentheses removed. If
        a translation is not found in the current language's translation
        strings, the original text is returned.

        The string lookup is case-sensitive since different languages have
        different rules around casing.

        It is not possible to display text with parentheses in it since this
        method will remove them. If this is something you need, contact us and
        we can add that feature.

        """


        self.log.debug("Getting language for text: %s", text)
        if self.config and '(' in text and ')' in text:
            for match in self.find_text.findall(text):
                replacement_string = match
                text_string = replacement_string[1:-1]
                modified_string = text_string

                if (self.current_language in self.machine.config['languagestrings']
                        and text_string in self.machine.config['languagestrings']
                        [self.current_language]):
                    modified_string = (self.machine.config['languagestrings']
                        [self.current_language][text_string])

                text = text.replace(replacement_string, modified_string)

        return text

    def get_text(self, text, language):
        """Returns a translated text string for a specific language string.

        Args:
            text: The text string you'd like to get the replacement for.
            language: The language you'd like to lookup for the replacement.

        If the specific text string and language combination doesn't exist in
        the translation file, the original string is returned.

        The string lookup is case-sensitive.

        This method is similar to text(), except this method doesn't strip out
        the parentheses. (i.e. it's just used to look up what's "inside" the
        parentheses.)

        """
        if text in self.text_dict:
            return self.text_dict[text]
        else:
            return text


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
