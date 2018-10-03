Machine Variables in Code
=========================

You can use machine variables by calling into the MPF machine.

.. code-block:: python

   # read machine variable
   print(self.machine.get_machine_var("my_variable"))

   # configure variable to persist to disk and expire after 1 day (optional)
   # alternatively you can also use "machine_vars" in config to achieve the same
   self.machine.configure_machine_var("my_variable", persist=True, expire_secs=86400)

   # set a variable
   self.machine.set_machine_var("my_variable", 17)
