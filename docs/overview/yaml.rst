MPF's divergence for pure YAML
==============================

MPF uses the YAML file format for config and show files. That said, MPF diverges from the
`pure YAML 1.2 specification <http://www.yaml.org/spec/1.2/spec.html>`_ for unquoted strings
in a few ways. Those are cases where YAML guesses which data type the value is which led to
problems/confusion in the past:

**Values beginning with "+" are strings**

   The YAML spec essentially ignores a leading plus sign, so a value ``+1`` would be read
   in as the integer ``1``. However MPF needs to differentiate between ``+1`` and ``1`` since
   the plus sign is used to mean the value is a delta in certain situations, so MPF's YAML
   interfaces will process any numeric values with a leading plus sign as strings.

**Values beginning with a leading "0" are strings**

   The YAML spec will process values that are only digits 0-7 with leading zeros as octals.
   However MPF could have color values like ``050505`` which should be read as strings. So
   the MPF YAML interface processes any value with at least 3 digits and leading zeros as
   strings.

**"On" and "Off" values are strings**

   The YAML spec defines ``on`` and ``off`` values as bools. But many MPF users create show
   names called "on" and "off", so MPF's YAML processor interprets those as strings. (True,
   False, Yes, and No are still processes as bools.)

**Values with only digits and "e" are strings**

   The YAML spec will process a value like ``123e45`` as "123 exponent 45". Since those could
   be hex color codes, MPF's YAML interface processes values that are all digits with a single
   "e" character as strings.
