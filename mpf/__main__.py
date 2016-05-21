"""Command dispatcher of the Mission Pinball Framework."""
import sys
import mpf.commands


def main(args=None):
    """Dispatche commands to our handlers."""
    if args is None:
        args = sys.argv[1:]

    mpf.commands.run_from_command_line(args)

if __name__ == "__main__":
    main()
