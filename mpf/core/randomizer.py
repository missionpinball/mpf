"""Generic list randomizer."""
from uuid import uuid4
import random


class Randomizer:

    """Generic list randomizer."""

    def __init__(self, items, machine=None, template_type=None):
        """Initialise Randomizer."""
        self.fallback_event = None
        self.force_different = True
        self.force_all = False
        self.disable_random = False
        # self.loop - property which sets force_all=True if loop==False
        self.items = list()

        self._loop = True
        self._template_type = template_type
        self.data = None
        self._uuid = uuid4()

        if isinstance(items, (list, tuple)):
            for i in items:
                if isinstance(i, (tuple, list)):
                    this_item = i[0]
                    this_weight = int(i[1])
                else:
                    this_item = i
                    this_weight = 1
                # If a template_type is provided, convert the event into a conditional template
                if machine and template_type:
                    this_item = self.generate_template(machine, template_type, this_item)
                self.items.append((this_item, this_weight))

        elif isinstance(items, dict):
            for this_item, this_weight in items.items():
                # If a template_type is provided, convert the event into a conditional template
                if machine and template_type:
                    this_item = self.generate_template(machine, template_type, this_item)
                self.items.append((this_item, int(this_weight)))
                self.items.sort()
        else:
            raise AssertionError("Invalid input for Randomizer")

        self.data = dict()
        self._init_data(self.data)

    def __iter__(self):
        """Return iterator."""
        return self

    def __next__(self):
        """Return next."""
        if self.disable_random:
            return self._next_not_random()

        potential_nexts = list()

        if self.force_all:
            potential_nexts = [
                x for x in self.items if x[0] not in self.data['items_sent']]

        elif self.force_different:
            potential_nexts = [
                x for x in self.items if x[0] is not self.data['current_item']]

        if not potential_nexts:

            if not self._loop:
                raise StopIteration

            self.data['items_sent'] = set()

            # force different only works with more than 1 elements
            if self.force_different and len(self.items) > 1:
                potential_nexts = [x for x in self.items if x[0] is not (
                    self.data['current_item'])]
            else:
                potential_nexts = list(self.items)
        if potential_nexts and self._template_type:
            conditional_nexts = list()
            for event, weight in potential_nexts:
                if not event.condition:
                    conditional_nexts.append((event.name or event, weight))
                elif event.condition.evaluate({}):
                    conditional_nexts.append((event.name, weight))
            potential_nexts = conditional_nexts

        # If no events were found due to all conditions failing, return the fallback
        if not potential_nexts:
            return self.fallback_event

        self.data['current_item'] = self.pick_weighted_random(potential_nexts)
        self.data['items_sent'].add(self.data['current_item'])

        return self.data['current_item']

    @property
    def loop(self):
        """Return loop property."""
        return self._loop

    @loop.setter
    def loop(self, loop):
        """Set loop property."""
        if loop:
            self._loop = True
        else:
            self._loop = False
            self.force_all = True

    def _next_not_random(self):
        if self.data['current_item_index'] == len(self.items):
            if not self.loop:
                raise StopIteration

            self.data['current_item_index'] = 0

        self.data['current_item'] = (
            self.items[self.data['current_item_index']][0])

        self.data['current_item_index'] += 1

        return self.data['current_item']

    @staticmethod
    def _init_data(data_dict):
        """Initialise dict."""
        data_dict['current_item'] = None
        data_dict['items_sent'] = set()
        data_dict['current_item_index'] = 0  # only used with disable random

    def get_current(self):
        """Return current item."""
        if self.data['current_item']:
            return self.data['current_item']

        return self.__next__()

    def get_next(self):
        """Return next item."""
        return self.__next__()

    def generate_template(self, machine, template_type, value):
        if template_type == "event":
            return machine.placeholder_manager.parse_conditional_template(value)
        # Add additional template_type support here, as needed
        return value

    @staticmethod
    def pick_weighted_random(items):
        """Pick a random item.

        Args:
            items: Items to select from
        """
        total_weights = sum([x[1] for x in items])
        value = random.randint(1, total_weights)
        index_value = 0

        for item in items:
            index_value += item[1]
            if index_value >= value:
                return item[0]

        return items[-1][0]
