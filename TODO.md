# FAST Platform Rewrite TODO list for MPF 0.57

* Get rid of all communicator-level message waiting?

* Get FAST EXP tests working
* Finish the FAST machine reset test
* Add a test for ball ending?
* Merge fastpinball branch into mainline

* On startup, address switch changes coming in while everything is being reset. Add an init flag and ignore them until cleared?
* Delayed pulse. Add platform_setting for this.
* Test single wound with EOS? Is this a thing?
* Confirm recycle_ms when used with autofire rules
* Test game start & restart process
* Add a test for the "no config" case
* slots
* Find all the TODOs
* Implement the soft reset at startup / restart
* Figure out the config file errors / error logs to FAST site / etc.
* Single LED update task

Failing tests are
ERROR: test_scoring (mpf.tests.test_CustomCode.TestCustomCode)
And the FAST EXP and v1 tests