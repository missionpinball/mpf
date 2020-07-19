"""Scaffold YAMLs in your machine."""
import cmd
import os

from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip


class ScaffoldCli(cmd.Cmd):

    """Scaffolding for MPF."""

    intro = 'Welcome to the MPF scaffolding shell. Type help or ? to list commands.\n'
    prompt = "(scaffold) "

    def __init__(self, machine_path, stdin=None, stdout=None):
        """Initialise service cli."""
        super().__init__(stdin=stdin, stdout=stdout)
        self.machine_path = machine_path

    def _create_mode(self, name):
        """Create a mode."""
        # create mode folder
        os.mkdir(os.path.join(self.machine_path, "modes", name))
        # create config folder
        os.mkdir(os.path.join(self.machine_path, "modes", name, "config"))
        # create config file
        with open(os.path.join(self.machine_path, "modes", name, "config", "{}.yaml".format(name)), "w") as f:
            f.write("""#config_version=5

mode:
    start_events: ball_started
    priority: 100
""")

        self.stdout.write("Success: Created mode {}. Next step: Add it to your mode list.\n".format(name))

    @staticmethod
    def _create_show(name):
        del name
        raise AssertionError("Not implemented")

    def do_copy(self, args):
        """Copy light positions from monitor to your config."""
        arguments = args.split(" ")
        if not arguments or len(arguments) != 2 or arguments[0] != "light_positions":
            self.stdout.write("Usage: copy light_positions your_light_config_file\n")
            return

        config_loader = YamlRoundtrip()
        config_name = arguments[1]
        try:
            monitor_config = config_loader.load("monitor/monitor.yaml")
        except Exception as e:  # pylint: disable-msg=broad-except
            self.stdout.write("Error while loading monitor/monitor.yaml: {}.\n".format(e))
            return

        try:
            lights_config = config_loader.load(config_name)
        except Exception as e:  # pylint: disable-msg=broad-except
            self.stdout.write("Error while loading {}: {}.\n".format(config_name, e))
            return

        if "light" not in monitor_config:
            self.stdout.write("Error: Monitor config does not contain a light section.\n")
            return

        if "lights" not in lights_config:
            self.stdout.write("Error: Config does not contain a lights section.\n")
            return

        lights_found = 0
        for light_name, light_config in lights_config['lights'].items():
            if light_name in monitor_config['light']:
                monitor_light_config = monitor_config['light'][light_name]
                lights_found += 1

                light_config['x'] = monitor_light_config['x']
                light_config['y'] = monitor_light_config['y']

        config_loader.save(config_name, lights_config)
        self.stdout.write("Success: Found {} lights.\n".format(lights_found))

    def do_create(self, args):
        """Create something."""
        arguments = args.split(" ")
        if not arguments:
            self.stdout.write("Usage: create mode/show [...]\n")
            return
        what = arguments.pop(0)
        if what == "mode":
            if len(arguments) != 1:
                self.stdout.write("Usage: create mode name\n")
                return
            self._create_mode(arguments[0])
        elif what == "show":
            if len(arguments) != 1:
                self.stdout.write("Usage: create show name\n")
                return
            self._create_show(arguments[0])
        else:
            self.stdout.write("Error: Unknown {}\n".format(what))
            return

    def do_exit(self, args):    # noqa
        """Exit scaffolding mode."""
        del args
        return True

    def do_quit(self, args):    # noqa
        """Exit scaffolding mode."""
        del args
        return True

    def do_EOF(self, args):     # noqa
        """Exit scaffolding mode."""
        del args
        return True


class Command:

    """Run the service cli."""

    def __init__(self, mpf_path, machine_path, args):
        """Run service cli."""
        del mpf_path
        del args

        cli = ScaffoldCli(machine_path)
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            # catch ctrl+c
            cli.do_exit("")

        # print a newline for a nice exit
        print()
