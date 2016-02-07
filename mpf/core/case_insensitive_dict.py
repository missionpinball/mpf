# Based on this: http://stackoverflow.com/questions/2082152/case-insensitive-dictionary

class CaseInsensitiveDict(dict):
    @classmethod
    def _k(cls, key):
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._convert_keys()

    def __getitem__(self, key):
        return super().__getitem__(self.__class__._k(key))

    def __setitem__(self, key, value):
        super().__setitem__(self.__class__._k(key), value)

    def __delitem__(self, key):
        return super().__delitem__(self.__class__._k(key))

    def __contains__(self, key):
        return super().__contains__(self.__class__._k(key))

    def has_key(self, key):
        return super().has_key(self.__class__._k(key))

    def pop(self, key, *args, **kwargs):
        return super().pop(self.__class__._k(key), *args, **kwargs)

    def get(self, key, *args, **kwargs):
        return super().get(self.__class__._k(key), *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        return super().setdefault(self.__class__._k(key), *args, **kwargs)

    def update(self, E=None, **F):
        super().update(self.__class__(E))
        super().update(self.__class__(**F))

    def _convert_keys(self):
        for k in list(self.keys()):
            v = super().pop(k)
            self.__setitem__(k, v)
