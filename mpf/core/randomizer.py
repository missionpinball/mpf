"""Generic list randomizer."""
import random


class Randomizer:

    """Generic list randomizer."""

    def __init__(self, items, machine=None, template_type='event'):
        """Initialize Randomizer."""
        self.fallback_value = None
        self.force_different = True
        self.force_all = False
        self.disable_random = False
        self.items = list()

        # self.loop - property which sets force_all=True if loop==False
        self._loop = True

        self._template_type = template_type
        self.data = None

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
                self.items.sort(key=lambda x: x[0].name or x[0])
        else:
            raise AssertionError("Invalid input for Randomizer")

        self.data = dict()
        self._init_data(self.data)

    def __iter__(self):
        """Return iterator."""
        return self

    def __next__(self, conditional_args=None):
        """Return next."""
        if not conditional_args:
            conditional_args = {}

        if self.disable_random:
            return self._next_not_random(conditional_args)

        potential_nexts = list()
        items = self._get_items(conditional_args)

        if self.force_all:
            potential_nexts = [
                x for x in items if x[0] not in self.data['items_sent']]

        elif self.force_different:
            potential_nexts = [
                x for x in items if x[0] is not self.data['current_item']]

        if not potential_nexts:

            if not self._loop:
                raise StopIteration

            self.data['items_sent'] = set()

            # force different only works with more than 1 elements
            if self.force_different and len(self.items) > 1:
                potential_nexts = [x for x in items if x[0] is not (
                    self.data['current_item'])]
            else:
                potential_nexts = list(items)

        # If no values were found due to all conditions failing, return the fallback
        if not potential_nexts:
            return self.fallback_value

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

    def _next_not_random(self, conditional_args):
        total_items = len(self.items)
        current_item_index = self.data['current_item_index']
        if current_item_index >= total_items:
            if not self.loop:
                raise StopIteration

            current_item_index %= total_items  # or we could just go to 0

        next_item_index = current_item_index

        rotated_option_list = self.items[next_item_index:] + self.items[:next_item_index]
        while len(rotated_option_list):
            next_item = rotated_option_list.pop(0)
            next_item_index += 1
            event = next_item[0]
            if not event.condition or (self._template_type and event.condition.evaluate(conditional_args)):
                break

        self.data['current_item'] = next_item
        self.data['current_item_index'] = next_item_index

        return next_item[0].name

    @staticmethod
    def _init_data(data_dict):
        """Initialize dict."""
        data_dict['current_item'] = None
        data_dict['items_sent'] = set()

        # only used with disable random, represents the index in the list _before_ conditional evaluation check
        data_dict['current_item_index'] = 0

    def get_current(self):
        """Return current item."""
        if self.data['current_item']:
            return self.data['current_item']

        return next(self)

    def get_next(self, conditional_args=None):
        """Return next item."""
        return next(self, conditional_args)

    def _get_items(self, conditional_args):
        if self._template_type:
            valid_items = list()
            for event, weight in self.items:
                if not event.condition:
                    valid_items.append((event.name or event, weight))
                elif event.condition.evaluate(conditional_args):
                    valid_items.append((event.name, weight))
            return valid_items
        return self.items

    @staticmethod
    def generate_template(machine, template_type, value):
        """Convert a string with conditions into a conditional event template object."""
        if template_type == "event":
            return machine.placeholder_manager.parse_conditional_template(value)
        # Add additional template_type support here, as needed
        return value

    @staticmethod
    def pick_weighted_random(items):
        """Pick a random item.

        Args:
        ----
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
