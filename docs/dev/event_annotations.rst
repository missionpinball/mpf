Annotating events for MPF docs
==============================

You usually write the following to post an event in code:

.. code-block:: python

  # this event is posted when something awesome happens
  self.machine.events.post("your_awesome_event", reason=what_happened)


This will work. However, nobody will know about your shiny new event. Therefore,
we want to document it for our users. Since it would be dublicate work to
document the event in code and in the docs, we use a custom docblock annotation:

.. code-block:: python

  self.machine.events.post("your_awesome_event", reason=what_happened)
  '''event: your_awesome_event

  desc: This event is posted when something awesome happens. We suggest that
  you play a loud sound and show some flashy slides when this happens.

  args:
    reason: The reason for this awesomeness is stated here.
  '''

The event should be added to the `event reference <https://missionpinball.org/events/>`_
on missionpinball.org.

Note: As of June 2023, the events list on missionpinball.org is no longer automatically generated.
