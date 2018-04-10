"""Service cli."""
import asyncio
import cmd

from terminaltables import AsciiTable

from mpf.core.bcp.bcp_socket_client import AsyncioBcpClientSocket


class ServiceCli(cmd.Cmd):

    """Commandline service mode for MPF."""

    intro = 'Welcome to the MPF service shell. Type help or ? to list commands.\n'
    prompt = "(service) "

    def __init__(self, bcp_client, loop, stdin=None, stdout=None):
        """Initialise service cli."""
        super().__init__(stdin=stdin, stdout=stdout)
        self.bcp_client = bcp_client
        # start service mode
        self.bcp_client.send("service", {"subcommand": "start"})
        self.loop = loop
        self._known_coils = None
        self._known_lights = None
        self._known_shows = None

    def _build_known_coils(self, list_coils_response):
        self._known_coils = []
        for coil in list_coils_response[1]["coils"]:
            self._known_coils.append(coil[2])

    def _build_known_lights(self, list_lights_response):
        self._known_lights = []
        for light in list_lights_response[1]["lights"]:
            self._known_lights.append(light[2])

    def _build_known_shows(self, list_shows_response):
        self._known_shows = []
        for show in list_shows_response[1]["shows"]:
            self._known_shows.append(show[0])

    def do_list_coils(self, args):
        """List all coils."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_coils"})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_coils"))
        data = [["Board", "Number", "Name"]]
        for coil in message[1]["coils"]:
            data.append([coil[0], coil[1], coil[2]])

        self._build_known_coils(message)
        table = AsciiTable(data)
        self.stdout.write(table.table + "\n")

    def do_list_shows(self, args):
        """List all shows."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_shows"})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_shows"))
        data = [["Name", "Token"]]
        for show in message[1]["shows"]:
            data.append([show[0], show[1]])

        self._build_known_shows(message)
        table = AsciiTable(data)
        self.stdout.write(table.table + "\n")

    def do_list_switches(self, args):
        """List all switches."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_switches"})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_switches"))
        data = [["Board", "Number", "Name", "State"]]
        for switch in message[1]["switches"]:
            data.append([switch[0], switch[1], switch[2], "closed" if switch[3] else "open"])

        table = AsciiTable(data)
        self.stdout.write(table.table + "\n")

    def do_list_lights(self, args):
        """List all lights."""
        del args
        self.bcp_client.send("service", {"subcommand": "list_lights"})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_lights"))
        data = [["Board", "Number", "Name", "Color"]]
        for light in message[1]["lights"]:
            data.append([light[0], light[1], light[2], light[3]])

        self._build_known_lights(message)
        table = AsciiTable(data)
        self.stdout.write(table.table + "\n")

    def complete_coil_pulse(self, text, line, start_index, end_index):
        """Autocomplete coil names."""
        return self.complete_coil_xxx(text, line, start_index, end_index)

    def complete_coil_enable(self, text, line, start_index, end_index):
        """Autocomplete coil names."""
        return self.complete_coil_xxx(text, line, start_index, end_index)

    def complete_coil_disable(self, text, line, start_index, end_index):
        """Autocomplete coil names."""
        return self.complete_coil_xxx(text, line, start_index, end_index)

    def complete_light_color(self, text, line, start_index, end_index):
        """Autocomplete light names."""
        return self.complete_light_xxx(text, line, start_index, end_index)

    def complete_light_off(self, text, line, start_index, end_index):
        """Autocomplete light names."""
        return self.complete_light_xxx(text, line, start_index, end_index)

    def complete_show_play(self, text, line, start_index, end_index):
        """Autocomplete show names."""
        return self.complete_show_xxx(text, line, start_index, end_index)

    def complete_show_stop(self, text, line, start_index, end_index):
        """Autocomplete show names."""
        return self.complete_show_xxx(text, line, start_index, end_index)

    def complete_show_xxx(self, text, line, start_index, end_index):
        """Autocomplete shows."""
        del line
        del start_index
        del end_index
        if not self._known_shows:
            self.bcp_client.send("service", {"subcommand": "list_shows"})
            message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_shows"))
            self._build_known_shows(message)

        if text:
            return [
                show for show in self._known_shows
                if show.startswith(text)
            ]
        else:
            return self._known_shows

    def complete_light_xxx(self, text, line, start_index, end_index):
        """Autocomplete lights."""
        del line
        del start_index
        del end_index
        if not self._known_lights:
            self.bcp_client.send("service", {"subcommand": "list_lights"})
            message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_lights"))
            self._build_known_lights(message)

        if text:
            return [
                light for light in self._known_lights
                if light.startswith(text)
            ]
        else:
            return self._known_lights

    def complete_coil_xxx(self, text, line, start_index, end_index):
        """Autocomplete coils."""
        del line
        del start_index
        del end_index
        if not self._known_coils:
            self.bcp_client.send("service", {"subcommand": "list_coils"})
            message = self.loop.run_until_complete(self.bcp_client.wait_for_response("list_coils"))
            self._build_known_coils(message)

        if text:
            return [
                coil for coil in self._known_coils
                if coil.startswith(text)
            ]
        else:
            return self._known_coils

    def _parse_args(self, args, args_with_default):
        while args:
            try:
                setting_arg = args.pop(0)
                setting_name, setting_value = setting_arg.split(":", 2)
                if setting_name not in args_with_default:
                    self.stdout.write("Setting {} not allowed. Allowed: {}.".format(setting_name, args_with_default))
                    return False

                args_with_default[setting_name] = setting_value
            except ValueError:
                self.stdout.write("Setting {} is expected as setting_name:setting_value.".format(setting_arg))
                return False
        return args_with_default

    def do_coil_pulse(self, args):
        """Pulse a coil."""
        arguments = args.split(" ")
        coil = arguments.pop(0)
        args = self._parse_args(arguments, {"pulse_ms": None, "pulse_power": None})
        if not args:
            return

        bcp_args = {"subcommand": "coil_pulse", "coil": coil}
        bcp_args.update(args)
        self.bcp_client.send("service", bcp_args)
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("coil_pulse"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_coil_enable(self, args):
        """Enable a coil (if possible for coil)."""
        arguments = args.split(" ")
        coil = arguments.pop(0)
        args = self._parse_args(arguments, {"pulse_ms": None, "pulse_power": None, "hold_power": None})
        if not args:
            return

        bcp_args = {"subcommand": "coil_enable", "coil": coil}
        bcp_args.update(args)
        self.bcp_client.send("service", bcp_args)
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("coil_enable"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_coil_disable(self, args):
        """Disable a coil."""
        self.bcp_client.send("service", {"subcommand": "coil_disable", "coil": args})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("coil_disable"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_show_play(self, args):
        """Play a show."""
        arguments = args.split(" ")
        show = arguments.pop(0)
        token = {}
        while arguments:
            try:
                token_arg = arguments.pop(0)
                token_name, token_value = token_arg.split(":", 2)
                token[token_name] = token_value
            except ValueError:
                self.stdout.write("Token {} is expected as token_name:token_value.".format(token_arg))
                return

        self.bcp_client.send("service", {"subcommand": "show_play", "show": show, "token": token})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("show_play"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_show_stop(self, args):
        """Stop a playing show."""
        self.bcp_client.send("service", {"subcommand": "show_stop", "show": args})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("show_stop"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_light_color(self, args):
        """Color a light."""
        try:
            light_name, color_name = args.split(" ", 2)
        except ValueError:
            # default to white
            light_name = args
            color_name = "white"
        self.bcp_client.send("service", {"subcommand": "light_color", "light": light_name, "color": color_name})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("light_color"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_light_off(self, args):
        """Turn off a light."""
        self.bcp_client.send("service", {"subcommand": "light_color", "light": args, "color": "off"})
        message = self.loop.run_until_complete(self.bcp_client.wait_for_response("light_color"))
        if message[1]["error"]:
            self.stdout.write("Error: {}\n".format(message[1]["error"]))
        else:
            self.stdout.write("Success\n")

    def do_monitor_switches(self, args):
        """Monitor switches."""
        pass
        # TODO: implement

    def do_exit(self, args):
        """Exit service mode."""
        del args
        self._exit()
        return True

    def do_quit(self, args):
        """Exit service mode."""
        del args
        self._exit()
        return True

    def do_EOF(self, args):   # noqa
        """Exit service mode."""
        del args
        self._exit()
        return True

    def _exit(self):
        # stop service mode
        self.bcp_client.send("service", {"subcommand": "stop"})
        self.loop.run_until_complete(self.bcp_client.wait_for_response("service_stop"))


class Command(object):

    """Run the service cli."""

    def __init__(self, mpf_path, machine_path, args):
        """Run service cli."""
        del mpf_path
        del machine_path
        del args

        reader, writer = asyncio.get_event_loop().run_until_complete(asyncio.open_connection("localhost", 5051))
        client = AsyncioBcpClientSocket(writer, reader)
        cli = ServiceCli(client, asyncio.get_event_loop())
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            # catch ctrl+c
            cli.do_exit("")

        # print a newline for a nice exit
        print()
