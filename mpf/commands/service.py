"""Service cli."""
import cmd


class ServiceCli(cmd.Cmd):

    """Commandline service mode for MPF."""

    intro = 'Welcome to the MPF service shell. Type help or ? to list commands.\n'
    prompt = "(service) "

    def do_list_coils(self, args):
        """List all coils."""
        pass
        # TODO: implement

    def do_list_switches(self, args):
        """List all switches."""
        pass
        # TODO: implement

    def do_list_lights(self, args):
        """List all lights."""
        pass
        # TODO: implement

    def do_coil_pulse(self, args):
        """Pulse a coil."""
        pass
        # TODO: implement

    def do_coil_enable(self, args):
        """Enable a coil (if possible for coil)."""
        pass
        # TODO: implement

    def do_coil_disable(self, args):
        """Disable a coil."""
        pass
        # TODO: implement

    def do_light_color(self, args):
        """Color a light."""
        pass
        # TODO: implement

    def do_light_off(self, args):
        """Turn off a light."""
        pass
        # TODO: implement

    def do_monitor_switches(self, args):
        """Monitor switches."""
        pass
        # TODO: implement

    def do_exit(self, args):
        """Exit service mode."""
        del args
        return True

    def do_quit(self, args):
        """Exit service mode."""
        del args
        return True

    def do_EOF(self, args):
        """Exit service mode."""
        del args
        return True


class Command(object):

    """Run the service cli."""

    def __init__(self, mpf_path, machine_path, args):
        del mpf_path
        del machine_path
        del args
        # TODO: start service mode
        cli = ServiceCli()
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            # catch ctrl+c
            pass

        # TODO: stop service mode
        # print a newline for a nice exit
        print()


