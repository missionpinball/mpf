rem Windows batch file to launch both MPF and the Media Controller at the same
rem time. You can pass command line options and args, like this:

rem mpf your_machine -x -v -V

@echo off

start "Media Controller" cmd /k python mc.py %*
start "MPF" cmd /k python mpf.py %*

rem The default options above pop up two new terminal windows, one for MPF and
rem one for the Media Controller. The new windows will stay open when the
rem programs exit so you can see any error messages if they crash.

rem If you want either of the pop-up windows to automatically close when done,
rem change "cmd /k" above to "cmd /c", like this:

rem If you want MPF to run in the current window instead of a popup, change the
rem line with "mpf.py" in it to this instead:

rem python mpf.py %*

rem The only downside to that every time you use CTRL+C to quit MPF, you'll get
rem the "Terminate Batch Job (Y/N)" prompt.
