@echo off

rem Windows batch file to launch both MPF and the Media Controller at the same
rem time which also closes the popup windows when MPF exits.
rem You can pass command line options and args, like this:

rem mpfx your_machine -x -v -V

start "Media Controller" cmd /c python mc.py %*
start "MPF" cmd /c python mpf.py %*

rem The default options above pop up two new terminal windows, one for MPF and
rem one for the Media Controller. The new windows will stay open when the
rem programs exit so you can see any error messages if they crash.

rem If you do not want either of the pop-up windows to automatically close when
rem done, change "cmd /c" above to "cmd /k".

rem If you want MPF to run in the current window instead of a popup, change the
rem line with "mpf.py" in it to this instead:

rem python mpf.py %*

rem The only downside to that is every time you use CTRL+C to quit MPF, you'll
rem get the "Terminate Batch Job (Y/N)" prompt.
