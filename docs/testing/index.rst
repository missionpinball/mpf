Automated Testing
=================

The MPF dev team are strong believers in automated testing, and we use a
`test-driven development (TDD) <https://en.wikipedia.org/wiki/Test-driven_development>`_ process for developing MPF
itself. (At the time of this writing, there are over 800 unit tests for MPF and MPF-MC, each which contain dozens of
individual tests.)

We have extended Python's built-in unittest TestCase class for MPF-specific tests, including mocking critical internal
elements and adding assertion methods for MPF features.

You can run built-in tests to test MPF itself or extend them if you think you found a bug or if you're adding features to
MPF. We have also built TestCase classes you can use to write unittests for your own machine. Read on for details:

.. toctree::
   :maxdepth: 1

   running_mpf_tests
   writing_mpf_tests
   writing_machine_tests
   fuzz_testing