from uuid import uuid4
import random


class Randomizer(object):

    def __init__(self, machine, items, memory='player'):

        self.force_different = True
        self.force_all = False
        self.disable_random = False
        # self.loop - property which sets force_all=True if loop==False
        self.items = list()

        self._loop = True
        self._machine = machine
        self._uuid = uuid4()
        self._data = None
        self._player_memory = True

        assert(isinstance(items, list) or isinstance(items, tuple))

        for i in items:
            if hasattr(i, '__iter__'):
                this_item = i[0]
                this_weight = int(i[1])
            else:
                this_item = i
                this_weight = 1

            self.items.append((this_item, this_weight))

        if memory == 'player':
            self._player_memory = True
        elif memory == 'machine':
            self._player_memory = False

            self._data = dict()
            self._init_data(self._data)

        else:
            raise ValueError("Memory should be 'machine' or 'player")

    def __iter__(self):
        return self

    def __next__(self):

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

            if self.force_different:
                potential_nexts = [x for x in self.items if x[0] is not (
                    self.data['current_item'])]
            else:
                potential_nexts = [x for x in self.items]

        self.data['current_item'] = self.pick_weighted_random(potential_nexts)
        self.data['items_sent'].add(self.data['current_item'])

        return self.data['current_item']

    @property
    def data(self):
        if self._player_memory:
            try:
                if not self._machine.game.player[self._uuid]:
                    self._machine.game.player[self._uuid] = dict()
                    self._init_data(self._machine.game.player[self._uuid])
            except AttributeError:
                raise AssertionError("Cannot access 'player memory' Randomizer"
                                     " as there is no active game or player")

            return self._machine.game.player[self._uuid]

        else:
            return self._data

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, loop):
        if loop:
            self._loop = True
        else:
            self._loop = False
            self.force_all = True

    def _next_not_random(self):
        if self.data['current_item_index'] == len(self.items):
            if not self.loop:
                raise StopIteration
            else:
                self.data['current_item_index'] = 0

        self.data['current_item'] = (
            self.items[self._data['current_item_index']][0])

        self.data['current_item_index'] += 1

        return self.data['current_item']

    def _init_data(self, data_dict):
        data_dict['current_item'] = None
        data_dict['items_sent'] = set()
        data_dict['current_item_index'] = 0  # only used with disable random

    def get_current(self):
        if self.data['current_item']:
            return self.data['current_item']
        else:
            return self.__next__()

    def get_next(self):
        return self.__next__()

    @staticmethod
    def pick_weighted_random(items):

        total_weights = sum([x[1] for x in items])
        value = random.randint(1, total_weights)
        index_value = 0

        for item in items:
            index_value += item[1]
            if index_value >= value:
                return item[0]

        return items[-1][0]
