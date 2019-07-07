"""Convert segment mappings from https://github.com/dmadison/LED-Segment-ASCII to our format."""
import argparse
import sys
import re

seg16 = ['dp', 'u', 't', 's', 'r', 'p', 'n', 'm', 'k', 'h',
         'g', 'f', 'e', 'd', 'c', 'b', 'a']
seg14 = ['dp', 'l', 'm', 'n', 'k', 'j', 'h', 'g2',
         'g1', 'f', 'e', 'd', 'c', 'b', 'a']
seg7 = ['dp', 'g', 'f', 'e', 'd', 'c', 'b', 'a']


def processfile(filename, segtable, class_name):
    """Process file."""
    ascii_char = 32
    with open(filename) as f:
        for line in f:
            m = re.search('.*0b([01]+), /\\* (.+) \\*/', line)
            if m:
                segs = m.group(1)
                char = m.group(2)

                members = ""
                for i, seg in enumerate(segs):
                    members += "{}={}, ".format(segtable[i], seg)

                print('{}: {}({}char="{}"),'.format(ascii_char, class_name, members, char.replace('"', '\\"')))

                ascii_char += 1


def main():
    """Parse args and start processing."""
    parser = argparse.ArgumentParser(description='File to load')

    parser.add_argument('--mode', type=int, choices=[7, 14, 16], help='mode', default=14)
    parser.add_argument('files', nargs='+')

    args = parser.parse_args()
    if args.mode == 16:
        segtable = seg16
        class_name = "SixteenSegments"
    elif args.mode == 7:
        segtable = seg7
        class_name = "SevenSegments"
    elif args.mode == 14:
        segtable = seg14
        class_name = "FourteenSegments"
    else:
        raise AssertionError("Invalid mode.")

    for f in args.files:
        processfile(f, segtable, class_name)


if __name__ == '__main__':
    sys.exit(main())
