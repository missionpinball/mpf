reset (BCP command)
===================

This command notifies the media controller that the pin controller is in the process of performing
a reset. If necessary, the media controller should perform its own reset process. The media
controller *must* respond with a :doc:`reset_complete </bcp/reset_complete>` command when finished.

Origin
------
Pin controller

Parameters
----------
None

Response
--------
:doc:`reset_complete </bcp/reset_complete>` when reset process has finished

