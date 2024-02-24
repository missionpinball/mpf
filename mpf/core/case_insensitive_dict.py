"""Case insensitive dict."""
# Based on this: http://stackoverflow.com/questions/2082152/case-insensitive-dictionary
from typing import List


class CaseInsensitiveDict(dict):

    """A dict which lowercases all keys."""

    __slots__ = []  # type: List[str]

    @staticmethod
    def lower(key):
        """Lowercase the key."""
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        """initialize case insensitve dict."""
        super().__init__(*args, **kwargs)
        self._convert_keys()

    def __getitem__(self, key):
        """Return item for key."""
        return super().__getitem__(self.__class__.lower(key))

    def __setitem__(self, key, value):
        """Set item for key to value."""
        super().__setitem__(self.__class__.lower(key), value)

    def __delitem__(self, key):
        """Delete item for key."""
        return super().__delitem__(self.__class__.lower(key))

    def __contains__(self, key):
        """Check if dict contains a key."""
        return super().__contains__(self.__class__.lower(key))

    def pop(self, key, *args, **kwargs):
        """Retrieve and delete a value for a key."""
        return super().pop(self.__class__.lower(key), *args, **kwargs)

    def get(self, key, *args, **kwargs):
        """Return item for key."""
        return super().get(self.__class__.lower(key), *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        """Set defaults."""
        return super().setdefault(self.__class__.lower(key), *args, **kwargs)

    def update(self, e=None, **f):
        """Update a value for a key."""
        super().update(self.__class__(e))
        super().update(self.__class__(**f))

    def _convert_keys(self):
        for k in list(self.keys()):
            v = super().pop(k)
            self.__setitem__(k, v)
