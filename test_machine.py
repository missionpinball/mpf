#!/usr/bin/python
if __name__ == "__main__":
    import unittest
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Run tests for a machine')

    parser.add_argument("machine_path", help="Path of the machine folder.")

    parser.add_argument("-v",
                        action="store_const", dest="verbosity", const=2,
                        default=1, help="Enables verbose logging")

    args = parser.parse_args()

    sys.path.insert(0, 'machine_files/' + args.machine_path + "/")

    all_tests = unittest.TestLoader().discover('machine_files/' + args.machine_path + "/")
    unittest.TextTestRunner(verbosity=args.verbosity).run(all_tests)
