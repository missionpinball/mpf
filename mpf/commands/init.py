"""Command to initialize an MPF project folder."""

import os
import pathlib
import shutil

SUBCOMMAND = True
INITIAL_MODES = ("attract", "base")


class Command:

    """Initializes an MPF project folder."""

    __slots__ = ("path", )

    def __init__(self, argv, path):
        """Generate config and mode folders."""
        # If a path is provided, use it
        if len(argv) > 1:
            path = os.path.join(path, argv[1])
        self.path = path

        print(f"Initializing MPF project at path {self.path}")

        try:
            os.stat(self.path)
        except FileNotFoundError:
            os.makedirs(self.path)

        self.generate_config_file()
        self.generate_mode_folder()

        print("MPF project initialization complete!")

    def generate_config_file(self):
        """Create a config folder and default config.yaml file."""
        config_dir = os.path.join(self.path, "config")
        try:
            os.stat(config_dir)
        except FileNotFoundError:
            os.mkdir(config_dir)

        config_file = os.path.join(config_dir, "config.yaml")
        try:
            os.stat(config_file)
        except FileNotFoundError:
            base_config_file = os.path.join(pathlib.Path(__file__).parent.absolute(), "templates/config.yaml")
            shutil.copy2(base_config_file, config_file)

    def generate_mode_folder(self):
        """Create mode folder and default mode subfolders."""
        mode_dir = os.path.join(self.path, "modes")
        try:
            os.stat(mode_dir)
        except FileNotFoundError:
            os.mkdir(mode_dir)

        for mode in INITIAL_MODES:
            mode_path = os.path.join(mode_dir, mode, "config")
            try:
                os.stat(mode_path)
            except FileNotFoundError:
                os.makedirs(mode_path)
            mode_config = os.path.join(mode_path, f"{mode}.yaml")
            try:
                os.stat(mode_config)
            except FileNotFoundError:
                mode_config_template = os.path.join(pathlib.Path(__file__).parent.absolute(), f"templates/{mode}.yaml")
                shutil.copy2(mode_config_template, mode_config)
