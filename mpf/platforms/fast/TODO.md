# FAST Platform Rewrite TODO list for MPF 0.57

## Features to add

* Neuron, add support for delayed pulse (Mode 30). This should be added via a `platform_settings:` coil config entry, and then also should "just work" for autofire coils and/or with autofire overwrite rules.
* Support next / previous for EXP LEDs
* RGBW LEDs on EXP bus (Eli will add functionality to the EXP boards that will take RGB colors and convert them to RGBW, so all we'll have to add is a way to specify which LEDs are RGBW so we can send the correct config commands.)
* Add ability to not probe the serial ports for platforms where the order does not change (e.g. everything but windows.) This will speed up the initial load time. (though only by about 100ms) We will still use the USB PID/VID to identify which serial ports are connected to which devices, we just won't actually probe them to verify their IDs.

## Things to verify / check / confirm

* Digital driver, confirm? Initial config?
* Verify driver enable for neuron, with disable later
* Find all the TODOs

## Tests Needed

* Auto port detection
* AC overwrites

## Platform interfaces yet to update / add

* Audio
* Emulation (start / stop / what else?)
* DMD
* Segment displays v1 (move over existing functionality)
* Segment displays v2 (switch to per-segment control and binary commands, full RGB support for different colors per segment, etc.)
* PC Control (via the Neuron and Audio interface)
* Smart power control features (waiting on FAST to release firmware)

## Refactoring

* Move FAST devices on EXP and breakout boards to mixin classes. e.g. LEds are a mixin class, servos are a mixin class, so the config for an EXP-0071 would pull in those two mixin classes rather than having device specific code in the base class.
* Figure out the config file errors / error logs to FAST site / etc. Currently there is no consistency, need to figure out which errors we link to the web, come up with a template and URLs to display them, etc.
* Single LED update task. Currently the LED update task is per EXP board which means they can be off by a few ms. We should have a single LED update task that runs at the same time for all boards.
* Change EXP `led_hz` setting to `led_update_ms` or something (specify in ms and not hertz since that's how the hardware works. Also enforce multiples of 32ms since that's the hw update speed.)

## MPF general

Thinking about the issue where a spinner rip can cause the watchdog to fail. We need to make sure that the watchdog is not blocked by any of the event handlers taking longer to run than the events are coming in. I was thinking about some option for a priority something or other for the watchdog task, but then I read Lin's comment about how he polls for switches instead of receiving events live and I wonder if we should re-architect the MPF event system to be more like that. i.e. have a task that polls for events and then calls the event handlers. That way the watchdog task could have a higher priority than the event handler task and it would always be able to run. (And we could also have a priority for the event handler task so that it could be higher than the main MPF task, etc.)

Frankly we could poll for switches then too. I guess there's a reason that people do things this way? On the other hand, meh. I don't know how much work it will be, and what else will it break? We could do it in a branch and see what happens, but, dunno, meh....

This would also solve a couple of other timeout issues that have popped up over the years...
