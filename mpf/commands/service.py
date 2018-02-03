"""Service cli."""
import asyncio
import cmd

from terminaltables import AsciiTable

from mpf.core.bcp.bcp_socket_client import AsyncioBcpClientSocket


class ServiceCli(cmd.Cmd):

    """Commandline service mode for MPF."""

    intro = 'Welcome to the MPF service shell. Type help or ? to list commands.\n'
    prompt = "(service) "

    def __init__(self, bcp_client):
        """Initialise service cli."""
        super().__init__()
        self.bcp_client = bcp_client

    def do_list_coils(self, args):
        """List all coils."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_coils"})
        message = asyncio.get_event_loop().run_until_complete(self.bcp_client.wait_for_response("list_coils"))
        data = [["Board", "Number", "Name"]]
        for coil in message[1]["coils"]:
            data.append([coil[0], coil[1], coil[2]])

        table = AsciiTable(data)
        print(table.table)

    def do_list_switches(self, args):
        """List all switches."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_switches"})
        message = asyncio.get_event_loop().run_until_complete(self.bcp_client.wait_for_response("list_switches"))
        data = [["Board", "Number", "Name", "State"]]
        for switch in message[1]["switches"]:
            data.append([switch[0], switch[1], switch[2], "closed" if switch[3] else "open"])

        table = AsciiTable(data)
        print(table.table)

    def do_list_lights(self, args):
        """List all lights."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_lights"})
        message = asyncio.get_event_loop().run_until_complete(self.bcp_client.wait_for_response("list_lights"))
        data = [["Board", "Number", "Name", "Color"]]
        for light in message[1]["lights"]:
            data.append([light[0], light[1], light[2], light[3]])

        table = AsciiTable(data)
        print(table.table)

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

    @staticmethod
    def do_exit(args):
        """Exit service mode."""
        del args
        return True

    @staticmethod
    def do_quit(args):
        """Exit service mode."""
        del args
        return True

    @staticmethod
    def do_EOF(args):   # noqa
        """Exit service mode."""
        del args
        return True


class Command(object):

    """Run the service cli."""

    def __init__(self, mpf_path, machine_path, args):
        """Run service cli."""
        del mpf_path
        del machine_path
        del args

        reader, writer = asyncio.get_event_loop().run_until_complete(asyncio.open_connection("localhost", 5051))
        client = AsyncioBcpClientSocket(writer, reader)
        # start service mode
        client.send("service", {"subcommand": "start"})
        cli = ServiceCli(client)
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            # catch ctrl+c
            pass

        # stop service mode
        client.send("service", {"subcommand": "stop"})
        asyncio.get_event_loop().run_until_complete(client.wait_for_response("service_stop"))
        # print a newline for a nice exit
        print()
