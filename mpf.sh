#!/bin/bash

# To use this, run ./mpf.sh as if you were launching mpf.py or mc.py.
# Example:
#
# ./mpf.sh demo_man -c proc -vV
#
# Command arguments will be passed to both processes.

# This code will launch mc in a new window and require you to switch windows
# and Ctrl-C out of each

x-terminal-emulator -e "python mc.py '$@'"
python mpf.py "$@"

# The line below will launch both processes in the same terminal window
# with the output of BOTH processes going to the same window
#
# You will have to press Ctrl-C twice to kill both of them and return to
# the prompt. To use, comment out the two commands above and uncomment the 
# line below.

#python mc.py "$@" & python mpf.py "$@" && echo "Killed both processes"

