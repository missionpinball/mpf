"""Scaffold YAMLs in your machine."""
import cmd
import os


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
        raise AssertionError("Not implemented")

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
        del machine_path
        del args

        cli = ScaffoldCli(os.getcwd())
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            # catch ctrl+c
            cli.do_exit("")

        # print a newline for a nice exit
        print()
