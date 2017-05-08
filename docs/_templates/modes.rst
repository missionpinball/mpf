self.machine.modes.{name}
{module_underline}

.. autoclass:: {full_path_to_class}
   :members:
   :show-inheritance:
   :exclude-members: mode_init, mode_start, mode_stop

   .. rubric:: Accessing the {name} mode via code

   You can access the {name} mode from anywhere via ``self.machine.modes.{name}``.

   .. rubric:: Methods & Attributes

   The {name} mode has the following methods & attributes available. Note that methods & attributes inherited from
   the base Mode class are not included here.