Post variables via self.machine.events.post:
============================================
for basic info on ``self.machine.events.post`` and how to add event_handlers check the following section

http://developer.missionpinball.org/en/dev/api/self.machine.events.html?highlight=event_handler

The best example here is to use the communication between MPF and MPF MC.
MPF MC can pretty much only read variables from ``self.player`` from MPF (``self.mc.player`` in MC),  however you simply don't want
to create extra variables in here just to make it readable readable in MC. This would result in having to much unnecessary data. 
Instead you can use ``self.machine.events.post`` just like you would write a function in python.

For example we set this up in a mode code in MPF:

.. code-block:: python

  variable_i_want_to_send = "King of the Hill"
  more_data_i_want_to_send = "1st"
  self.machine.events.post('awesome_event', data1=variable_i_want_to_send, data2=more_data_i_want_to_send)

It should always start with the ``event`` that you want to post. After this you can only add ``positional arguments``.
In MC code we create a function that will be activated once the event is posted. Make sure you have added a event_handler first or else it won't work.

.. code-block:: python
    
  def awesome_event(self, data1, data2, **kwargs):
    print("i really love the game {} I always end up {}".format(data1, data2)

That is all there is to it.
