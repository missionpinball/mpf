"""Example Scriptlet which shows different things you can do."""

from mpf.system.scriptlet import Scriptlet  # This import is required


class YourScriptletName(Scriptlet):  # Change `YourScriptletName` to whatever you want!
    """To 'activate' your Scriptlet:
        1. Copy it to your machine_files/<your_machine_name>/Scriptlets/ folder
        2. Add an entry to the 'Scriptlets:' section of your machine config files
        3. That entry should be 'your_Scriptlet_file_name.YourScriptletName'
    """

    def on_load(self):
        """Called automatically when this Scriptlet is loaded."""

        # add code here to do whatever you want your Scriptlet to do when the
        # machine boots up.

        # This example Scriptlet has lots of different examples which show (some)
        # of the things you can do. Feel free to delete everything from here on
        # down when you create your own Scriptlet.

        # you can access the machine object via self.machine, like this:
        print(self.machine)
        print(self.machine.game)
        # etc.

        # you can access this Scriptlet's name (based on the class name above):
        print(self.name)  # will print `YourScriptletName` in this case

        # you can write to the log via self.log:
        # The logger will be prefaced with Scriptlet.YourScriptletName
        self.log.info("This is my Scriptlet")
        self.log.debug("This is a debug-level log entry")

        # you can access machine configuration options via self.machine.config:
        print(self.machine.config['game']['balls per game'])

        # feel free to add your own entries to the machine configuration files,
        # like: self.machine.config['YourScriptlet']['Your Setting']

        # you can post events which other modules can pick up:
        self.machine.events.post('whatever_event_you_want')

        # you can register handlers to act on system events
        self.machine.events.add_handler('ball_add_live',
                                        self.my_handler)

        # you can create periodic timers that are called every so often
        from mpf.system.timing import Timer
        self.machine.timing.add(Timer(callback=self.my_timer, frequency=10))
        # (Or save a reference to the timer if you want to remove() it later.)

        # you can register a handler for the machine tick which will be called
        # every machine tick!
        self.machine.events.add_handler('timer_tick', self.tick)

        # you can create a task that can yield as needed

    def my_handler(self):
        # This is just an arbitrarily-named method which is the handler for
        # `ball_add_live_event` from the on_load(). Feel free to create as
        # many methods as you want in your Scriptlet!
        print("A new ball was added")

    def my_timer(self):
        print("another 10 seconds just passed")

    def tick(self):
        # this will run every single machine tick!!
        pass
