import os
import re
import tempfile

import shutil

from mpf.tests.MpfTestCase import MpfTestCase


class MpfDocTestCase(MpfTestCase):

    def __init__(self, config_string, methodName='test_config_parsing'):
        super().__init__(methodName)
        config_string = self.prepare_config(config_string)
        self.config_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.config_dir, "config"))
        with open(os.path.join(self.config_dir, "config", "config.yaml"), "w") as f:
            f.write(config_string)
        os.mkdir(os.path.join(self.config_dir, "modes"))
        os.mkdir(os.path.join(self.config_dir, "modes", "mode1"))
        self.addCleanup(self._delete_tmp_dir, self.config_dir)

    def getOptions(self):
        options = super().getOptions()
        # no cache since we are in a tmp folder anyway
        options['no_load_cache'] = True,
        options['create_config_cache'] = False
        return options

    def prepare_config(self, config_string):
        # add config_version if missing in example
        if not config_string.startswith("#config_version=5"):
            config_string = "#config_version=5\n" + config_string

        # inline invisible comments from documentation
        config_string = re.sub(r'#!\s+([^\n]+)', '\\1', config_string, re.MULTILINE)

        return config_string

    def getConfigFile(self):
        return "config.yaml"

    def getMachinePath(self):
        return self.config_dir

    def _delete_tmp_dir(self, config_dir):
        shutil.rmtree(config_dir)

    def test_config_parsing(self):
        pass
