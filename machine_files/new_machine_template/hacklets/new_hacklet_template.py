"""Template file you can customize to build your own machine-specific hacklets.
"""

from mpf.system.hacklet import Hacklet


class YourHackletName(Hacklet):  # Change `YourHackletName` to whatever you want!
    """To 'activate' this hacklet:
        1. Copy it to your machine_files/<your_machine_name>/hacklets/ folder
        2. Add an entry to the 'Hacklets:' section of your machine config files
        3. That entry should be 'your_hacket_file_name.YourHackletName'
    """

    def on_lood(self):
        """Called automatically when this hacklet is loaded."""
        pass
