"""Command to format yaml files."""
import sys

import os
from mpf.commands import MpfCommandLineParser

try:
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.shortcuts import message_dialog
    from prompt_toolkit.styles import Style
    from prompt_toolkit.shortcuts import button_dialog
    from prompt_toolkit.shortcuts import input_dialog
except ImportError:
    HTML = None
    message_dialog = None
    Style = None
    button_dialog = None
    input_dialog = None


SUBCOMMAND = True


class Command(MpfCommandLineParser):

    """Run a text unit test from cli."""

    def __init__(self, args, path):
        """Parse args."""
        super().__init__(args, path)
        self.current_path = path
        if self.in_machine_folder():
            self.machine_path = self.current_path

        if not HTML:
            raise AssertionError("You need to install the [cli] or [all] feature of mpf to use this.")

        self.example_style = Style.from_dict({
            'dialog': 'bg:#f2521d',
            'dialog frame.label': 'bg:#ffffff #000000',
            'dialog.body': 'bg:#000000 #FFFFFF',
            'dialog shadow': 'bg:#79290E',
            'dialog text-area': 'bg:#f2521d #FFFFFF'
        })

        self.creation_loop()

    def creation_loop(self):
        """Set up the main creation loop."""
        selection = button_dialog(
            title='Selection',
            text='What would you like to create?',

            buttons=[
                ('Machine', 'machine'),
                ('Mode', 'mode'),
                ('Show', 'show'),
                ('Cancel', 'cancel'),
            ],
            style=self.example_style
        ).run()
        if selection == 'machine':
            self.create_machine_config()
        elif selection == 'mode':
            if self.in_machine_folder():
                self.create_mode()
            else:
                self.show_not_in_machine_folder_dialog()
        elif selection == 'show':
            if self.in_machine_folder():
                self.create_show()
            else:
                self.show_not_in_machine_folder_dialog()
        else:
            sys.exit()
        self.creation_loop()

    def create_mode(self):
        """Create a mode."""
        mode_name = input_dialog(
            title='Mode',
            text='Cool, got a name for your mode?',
            style=self.example_style).run()

        # create mode folder
        mode_path = os.path.join(self.machine_path, "modes", mode_name)
        if not os.path.exists(mode_path):
            self.create_mode_structure(mode_name, mode_path, self.machine_path)
            message_dialog(
                title='Mode',
                text=HTML(
                    '''<style fg="green">Success:</style> Created mode {}.
                    \nDon\'t forget to add it to your mode list.'''.format(
                        mode_name)),
                style=self.example_style
            ).run()

        else:
            message_dialog(
                title='Mode',
                text=HTML(
                    '<style fg="red">Error:</style> A mode with this name exists already\nPlease pick another one'),
                style=self.example_style
            ).run()
            self.create_mode()

    def create_machine_config(self):
        """Create a machine config."""
        config_name = input_dialog(
            title='Machine Config',
            text='Please enter the name of your machine config:',
            style=self.example_style).run()

        if config_name is None:
            sys.exit()

        # create machine_config folder
        self.machine_path = os.path.join(self.current_path, config_name)

        if not os.path.exists(self.machine_path):

            self.create_machine_config_structure(config_name, self.machine_path)
            self.current_path = self.machine_path
            message_dialog(
                title='Mode',
                text=HTML(
                    '''<style fg="green">Success:</style> Created machine config {}.
                    \nYou can now create modes and shows.'''.format(
                        config_name)),
                style=self.example_style
            ).run()
        else:
            message_dialog(
                title='Mode',
                text=HTML(
                    '''<style fg="red">Error:</style> A machine config with this name exists already
                    \nPlease pick another one')'''),
                style=self.example_style
            ).run()
            self._create_machine_config()

    def create_show(self):
        """Create a show."""
        show_name = input_dialog(
            title='Mode',
            text='Cool, got a name for your show?',
            style=self.example_style).run()

        # create shows folder
        show_path = os.path.normpath(os.path.join(self.machine_path, "shows", show_name))
        shows_dir = os.path.normpath(os.path.join(self.machine_path, "shows"))

        if not os.path.exists(show_path):
            if self.in_machine_folder():
                self.create_show_structure(show_name, shows_dir, self.machine_path)
                message_dialog(
                    title='Shows',
                    text=HTML('<style fg="green">Success:</style> Created show {}.'.format(show_name)),
                    # text='Success: Created machine config {}.'.format(config_name),
                    style=self.example_style
                ).run()
            else:
                self.show_not_in_machine_folder_dialog()

        else:
            message_dialog(
                title='Mode',
                text=HTML(
                    '<style fg="red">Error:</style> A show with this name already exists\nPlease pick another one!'),
                style=self.example_style
            ).run()
            self._create_machine_config()

    def in_machine_folder(self):
        """Check if current directory is a machine folder."""
        return os.path.exists(os.path.join(self.current_path, "config"))

    def show_not_in_machine_folder_dialog(self):
        """Show error message if current directory is not a machine folder."""
        message_dialog(
            title='Wrong directory',
            text=HTML(
                '<style fg="red">Error:</style> You dont\'t seem to be in a machine folder.\nPlease switch to one!'),
            style=self.example_style
        ).run()
        sys.exit()

    @staticmethod
    def create_machine_config_structure(config_name, machine_path):
        """Create the basic hierarchy of a new machine folder including test and config files."""
        os.makedirs(os.path.normpath(machine_path))
        os.makedirs(os.path.normpath(os.path.join(machine_path, "config")))
        with open(os.path.normpath(os.path.join(machine_path, "config", "config.yaml")), "w") as f:
            f.write("#config_version=5")

        # create test folder
        os.makedirs(os.path.normpath(os.path.join(machine_path, "tests")))

        test_file_name = "test_{}.yaml".format(config_name)
        with open(os.path.normpath(os.path.join(machine_path, "tests", test_file_name)), "w"):
            pass

    @staticmethod
    def create_show_structure(show_name, shows_dir, machine_path):
        """Create the basic hierarchy of a new show folder."""
        if not os.path.exists(shows_dir):
            os.makedirs(shows_dir)
        file_content = "#show_version=5"
        show_file_name = "{}.yaml".format(show_name)
        config_path = os.path.normpath(os.path.join(machine_path, "shows", show_file_name))
        Command.write_config_file(config_path, file_content)

    @staticmethod
    def create_mode_structure(mode_name, mode_path, machine_path):
        """Create the basic hierarchy of a new mode folder."""
        os.makedirs(mode_path)
        # create config folder
        os.makedirs(os.path.normpath(os.path.join(machine_path, "modes", mode_name, "config")))
        # create config file
        file_content = """#config_version=5

            mode:
                start_events: ball_started
                priority: 100
            """
        config_file_name = "{}.yaml".format(mode_name)
        config_path = os.path.normpath(os.path.join(machine_path, "modes", mode_name, "config", config_file_name))
        Command.write_config_file(
            config_path, file_content)

    @staticmethod
    def write_config_file(path, config_file_content):
        """Create config files for machine folders or modes."""
        # create config file
        with open(path, "w") as f:
            f.write(config_file_content)
