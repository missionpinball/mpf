# FAST Platform Rewrite TODO list for MPF 0.57

* Add delayed pulse
* Do not block WD

* LED next/prev

* Digital driver, confirm? Initial config?
* Remove hw led fade time from nano?
* implement soft reset for EXP
* verify enable for neuron


* Delayed pulse. Add platform_setting for this.
* Test single wound with EOS? Is this a thing?
* Confirm recycle_ms when used with autofire rules
* Find all the TODOs
* Figure out the config file errors / error logs to FAST site / etc.
* Single LED update task

## Tests Needed

* Test auto port detection
* Test AC overwrites

## Platform interfaces yet to update / add

* Nano
* Retro
* Audio
* Move FAST devices to mixin classes
* DMD
* Segment

## MPF In general

* poll for events instead of direct callbacks?