self.machine.{name}.*
{module_underline}

.. autoclass:: {full_path_to_class}
   :members:
   :show-inheritance:
   :inherited-members:
   :exclude-members: config_section_name, setup_event_handlers, device_loaded_in_mode, device_added_to_mode, device_removed_from_mode, validate_and_parse_config, can_exist_outside_of_game, device_class_init, device_added_system_wide, configure_logging, debug_log, info_log, error_log, get_config_info, get_config_spec, load_config, load_platform_section, prepare_config, warning_log, ignorable_runtime_exception, get_monitorable_state, add_control_events_in_mode, overload_config_in_mode, remove_control_events_in_mode, post_update_event

   .. rubric:: Accessing {name} in code

   The device collection which contains the {name} in your machine is available via ``self.machine.{name}``. For
   example, to access one called "foo", you would use ``self.machine.{name}.foo``. You can also access {name} in
   dictionary form, e.g. ``self.machine.{name}['foo']``.

   You can also get devices by tag or hardware number. See the DeviceCollection documentation for details.

   .. rubric:: Methods & Attributes

   {cap_name} have the following methods & attributes available. Note that methods & attributes inherited from
   base classes are not included here.
