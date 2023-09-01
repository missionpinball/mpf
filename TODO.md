# FAST Platform Rewrite TODO list for MPF 0.57


* On startup, address switch changes coming in while everything is being reset. Add an init flag and ignore them until cleared?


## Driver commands

Thinking through the best way to do this.

Startup:

1. Initialize all drivers (based on actual I/O board driver counts, not MPF config) with `DL:xx,00,00,00,00,00,00,00,00`
2. Send initial configs to drivers based on MPF config. This would include modes, pulse times, recycles, etc. As well as autofire rules. Autofire rules should not be enabled since no game is in progress.
3. Save each config to the driver object

Alternate plan:

1. Wait until the configs are read in from the config files
2. create driver objects for each driver, set them to 00,00,00...
3. Update the driver objects with the configs from the config files
4. do a soft reset which will update all the drivers

Then when a command to activate a driver comes in, pulse(), enable(), disable(), etc. check to see if the current driver config matches or is compatible with what came in. If so, trigger it with `TL:`, otherwise send a `DL:` with a trigger now flag.

## Switch commands

Startup:


Next steps:

1. Update the drivers config tests so we have "one of each" of the driver types
2. Figure out the FSP commands for each
3. Write the tests, including zero'ed out for non configured ones
4. Start with non autofires.
5. Implement
6. Repeat for switches
7. Repeat for autofires

Clean up, last things

* Add a test for the "no config" case
* slots
* Find all the TODOs
* Implement the soft reset at startup / restart
* Figure out the config file errors / error logs to FAST site / etc.