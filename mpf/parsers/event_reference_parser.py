"""Returns all annotated events by class."""
import ast
import os

import re
from collections import namedtuple

from typing import List

EventReference = namedtuple("EventReference", ["event_name", "file_name", "config_section", "class_label",
                                               "desc", "args", "config_attribute"])


class EventReferenceParser:

    """Parser to find all annotated events in MPF."""

    def _parse_file(self, file_name) -> List[EventReference]:
        """Parse one file and return all events from that file."""
        try:
            with open(file_name) as f:
                my_ast = ast.parse(f.read())
        except Exception:
            raise AssertionError("Error while parsing {}".format(file_name))

        event_list = []

        for x in ast.walk(my_ast):
            if isinstance(x, ast.ClassDef):
                class_label = None
                config_section = None
                for statement in x.body:
                    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and \
                       isinstance(statement.targets[0], ast.Name) and isinstance(statement.value, ast.Str):
                        if statement.targets[0].id == "class_label":
                            class_label = str(statement.value.s)
                        elif statement.targets[0].id == "config_section":
                            config_section = str(statement.value.s)

                for y in ast.walk(x):
                    if not (isinstance(y, ast.Str) and (y.s.strip().lower().startswith('event:'))):
                        continue

                    event_dict = self._parse_string(y)
                    if not event_dict:
                        continue

                    event_list.append(EventReference(
                        event_name=event_dict["event"], file_name=file_name,
                        config_section=config_section if not event_dict["config_section"] else
                        event_dict["config_section"],
                        class_label=class_label if not event_dict["class_label"] else event_dict["class_label"],
                        desc=event_dict["desc"],
                        args=self._parse_args(event_dict["args"]),
                        config_attribute=event_dict["config_attribute"]))

        return event_list

    def _parse_string(self, string):
        string = '\n'.join(' '.join(line.split())
                           for line in string.s.split('\n'))

        string = string.replace('Event:', 'event:')
        string = string.replace('Desc:', 'desc:')

        try:
            string = string.replace('Args:', 'args:')
        except ValueError:
            pass

        final_dict = self._string_to_args_dict(string, ['event', 'desc',
                                                        'args', 'config_attribute',
                                                        'config_section', 'class_label'])

        if not final_dict['desc']:
            # not an events docstring
            return None

        return final_dict

    def _parse_args(self, args_string):
        if args_string is None:
            return {}

        args = list()
        for x in re.findall(r'\b(\w*)\b(?=:)', args_string):
            if x:
                args.append(x)

        args_dict = self._string_to_args_dict(args_string, args)

        return args_dict

    @staticmethod
    def _string_to_args_dict(string, args):
        index_starts = list()
        for arg in args:
            try:
                index_starts.append(string.index(arg + ':'))
            except ValueError:
                pass

        index_starts.sort()
        sliced_list = list()
        for x, start in enumerate(index_starts):
            try:
                sliced_list.append(string[start:index_starts[
                    x + 1]])
            except IndexError:
                sliced_list.append(string[start:])

        final_dict = dict()

        for entry in sliced_list:
            split_entry = entry.split(':', 1)
            final_dict[split_entry[0].strip()] = split_entry[1].strip()

        for arg in args:
            if arg not in final_dict:
                final_dict[arg] = None

        return final_dict

    def get_events_from_path(self, paths) -> List[EventReference]:
        """Parse paths recursively and return all events."""
        events = []
        for path in paths:
            for root, _, files in os.walk(path):
                for file in [x for x in files if x.endswith('.py')]:
                    events.extend(self._parse_file(os.path.join(root, file)))

        return events
