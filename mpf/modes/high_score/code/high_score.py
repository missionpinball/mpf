from mpf.system.data_manager import DataManager
from mpf.system.mode import Mode


class HighScore(Mode):

    def mode_init(self):
        self.data_manager = DataManager(self.machine, 'high_scores')
        self.high_scores = self.data_manager.get_data()
        self.config = self.machine.config['high_score']

        self._read_scores_from_disk()

    def _read_scores_from_disk(self):
        for category, entries in self.config['categories'].iteritems():

            try:
                for position, (label, (name, value)) in (
                        enumerate(zip(entries, self.high_scores[category]))):

                    self.machine.create_machine_var(
                        name=category + str(position + 1) + '_label',
                        value=label)
                    self.machine.create_machine_var(
                        name=category + str(position + 1) + '_name',
                        value=name)
                    self.machine.create_machine_var(
                        name=category + str(position + 1) + '_value',
                        value=value)

            except KeyError:
                pass

    def mode_start(self, **kwargs):
        pass

        # see if any players have the high scores

