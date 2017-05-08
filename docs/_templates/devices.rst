self.machine.{name}.*
{module_underline}

.. autoclass:: {full_path_to_class}
   :members:
   :show-inheritance:

   .. rubric:: Accessing {name} in code

   The device collection which contains the {name} in your machine is available via ``self.machine.{name}``. For
   example, to access one called "foo", you would use ``self.machine.{name}.foo``. You can also access {name} in
   dictionary form, e.g. ``self.machine.{name}['foo']``.

   You can also get devices by tag or hardware number. See the DeviceCollection documentation for details.

   .. rubric:: Methods & Attributes

   {cap_name} have the following methods & attributes available. Note that methods & attributes inherited from
   base classes are not included here.
