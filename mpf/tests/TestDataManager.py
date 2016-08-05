"""In-memory DataManager."""
from mpf.core.data_manager import DataManager


class TestDataManager(DataManager):

    def __init__(self, data):
        self.data = data

    def save_all(self, data=None, delay_secs=0):
        pass
