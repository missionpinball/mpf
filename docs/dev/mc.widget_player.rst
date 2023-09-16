self.mc.widget_player
=============

Accessing the widget_player in code
---------------------
The widget player is available via: ``self.mc.widget_player``

Methods & Attributes
---------------------
``play(settings, context, calling_context)``

``Add``, ``update`` or ``remove`` widget based on config

Settings:
^^^^^^^^^^^^^^^
Holds all the data for building the widget

Context:
^^^^^^^^^^^^^^^
Should be named to the name of the mode.

Calling_context:
^^^^^^^^^^^^^^^
Should be set to ``None`` by default.


Diving into the Settings of a Widget in code
---------------------
You might encounter some situations where you need a bit more freedom for creating a widget.
In the example here will be taking a look on how to reuse a predefined widget from the config
file and create some overrides to change or add a few settings.

So here is our base ``widget`` from the config file that we will be using.

.. code-block:: mpf-config

    widgets:
        some_image_widget:
          - type: image
            image: this_image_is_wrong
            y: 20
            x: 35

Refer to the widget section in the docs for more info on how to set it up:
https://missionpinball.org/mc/widgets/

Writing the settings to show/play this widget in code
^^^^^^^^^^^^^^^
To use ``self.mc.widget_player.play(settings, context, calling_context)`` it needs 3 values.

Context can be set to your mode name or something else from the machine.
Calling_context can be set to ``None``

.. code-block:: python

  context = "base"
  calling_context = None

When it comes to the settings we start with the following:

.. code-block:: python

  settings = {
    "some_image_widget": {
       "action": "add",
       "key": "my_image"
        }
      }

You need to add ``action`` and ``key`` to make the ``widget`` work.
Refer to the ``widget_player`` section for more info on these and what other functions can be added:
https://missionpinball.org/config_players/widget_player/

Now you can show the pre-defined widget from the config file.

``self.mc.widget_player.play(settings, context, calling_context)``

Overriding widget_settings from the widget
^^^^^^^^^^^^^^^
Now that you can play a widget it we will make some changes to it.
In this follow up example we will be changing the image by changing the string.
First we will define a ``variable`` which will hold our image name. (for example of a character)

.. code-block:: python

  character_name = some_function_for_retrieving_a_string()
  image_name = “character_{}_profile_image”.format(character_name)

To keep things organized in the image folder we made a prefix for the image.
Make sure you add the images with the right syntax in the image folder.

The following code shows how to override an image and x-coordinate

.. code-block:: python

  settings = {
      "some_image_widget": {
         "action": "add",
         "key": "my_image",
         "widget_settings": {
             "image": image_name,
             "x": 400,
              }
          }
       }

You can ``change``/``add`` everything this way from the related type of ``widget``, or the common settings for all widgets.
Refer to the common settings for a overview of all settings.

https://missionpinball.org/mc/widgets/common_settings/

Just make sure you format this way

Now you can show the ``widget`` from the config file with the image and position override.
``self.mc.widget_player.play(settings, context, calling_context)``

You can override everything, even the ``type`` of your ``widget``.

Overriding animations from a widget
---------------------
Again we continue with the last example. We will be adding animation to the widget.
There are 2 ways to do this. You can either call predefined animations from the config file,
or create an animation from within the widget.


Creating animation from predefined animations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The easiest thing is to change/add pre-defined animations.
See chapter 9 of widget animation for more info on this:
https://missionpinball.org/mc/widgets/animation/

.. code-block:: python

  settings = {
      "some_image_widget": {
          "action": "add",
          "key": "my_image",
          "widget_settings": {
              "image": image_name,
              "x": 400,
              “animations”: {
                  “some_event”: [
                      {"named_animation": "ani_1"},
                      {"named_animation": "ani_2"},]
                  }
              }
        }

Make sure that after defining the event you put the animations in a list ``[]``. And put every animation between brackets ``{}``.
``“named_animation”`` is called like that, you don’t need to change it in something else.

Creating/overriding animation from within the widget
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When creating the animations within the widget, you want to make sure that you also want to create a list in here.

.. code-block:: python

    settings = {
        "some_image_widget": {
            "action": "add",
            "key": "my_image",
            "widget_settings": {
                "image": image_name,
                "x": 400,
                “animations”: {
                    “some_event”: [{
                        "property": [‘x’, ‘y’],
                        “value”: [str(100), str(32)],
                        “duration”: 0.5,
                        },{
                        "property": [‘x’, ‘y’],
                        “value”: [str(-1000), str(-25)],
                        “duration”: 1 },],
                  }
            }
     }

So here are a few things to keep an eye on. ``property`` and ``value`` are put into a list ``[]``.
Also ``value`` needs to be converted to a ``string``. (I have no idea why) the code won’t work with a integer.
Make sure you put every animation between brackets ``{}``.

Final word
----------
Make sure to keep an eye on the syntax. The amount of brackets ``{}`` and commas ``,`` are a great recipe for problems.
Remember that you can swap all strings and value’s out.
