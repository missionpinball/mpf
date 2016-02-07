"""Template file you can customize to build your own machine-specific Scriptlets.
"""

from mpf.core.scriptlet import Scriptlet


class YourScriptletName(Scriptlet):  # Change `YourScriptletName` to whatever you want!
    """To 'activate' this Scriptlet:
        1. Copy it to your machine_files/<your_machine_name>/Scriptlets/ folder
        2. Add an entry to the 'Scriptlets:' section of your machine config files
        3. That entry should be 'your_hacket_file_name.YourScriptletName'
    """

    def on_load(self):
        """Called automatically when this Scriptlet is loaded."""
        pass
