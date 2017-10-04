"""In-memory DataManager."""
from mpf.core.data_manager import DataManager


class TestDataManager(DataManager):

    """A patched version of the DataManager which is used in unit tests.
    
    The main change is that the ``save_all()`` method doesn't actually
    write anything to disk so the tests don't fill up the disk with
    unneeded data.
    
    """

    def __init__(self, data):
        self.data = data

    def _trigger_save(self):
        pass
