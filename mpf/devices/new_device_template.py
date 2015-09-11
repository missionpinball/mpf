""" Template file for a new device driver."""

# Documentation and more info at http://missionpinball.com/mpf

# Search this file for 'YourNewDevice' and replace with your device name

from mpf.system.device import Device


class YourNewDevice(Device):

    config_section = 'your_new_devices'
    collection = 'your_new_devices'
    class_label = 'your_new_device'

    """ The two class attributes above control how devices based on this class
    are configured and how they're presented to the MPF.

    `config_section` is the name of the section in the machine configuration
    files that contains settings for this type of device. The game programmer
    would then create subsections for each device of this type, with individual
    settings under each one.

    For example, in the machine configuration files:

    YourNewDevices:
        device1:
            setting1: foo
            setting2: bar
            tags: tag2, tag3
            label: A plain english description of this device
        device2:
            setting1: foo
            setting2: bar
            tags: tag1, tag2
            label: A plain english description of this device

    `collection` is the DeviceCollection instance that will be created to hold
    all the devices of this new type. For example, if collection is
    'yournewdevice', a collection will be created which is accessible via
    self.machine.yournewdevices. """

    @classmethod
    def device_class_init(cls, machine):
        """This @classmethod is optional, but is called automatically before
        individual devices based on this device class are created. You can use
        it for any system-wide settings, configurations, or objects that you
        might need for these types of devices outside of the individual devices
        themselves.

        For example, led.py uses this to make sure the global fade_ms default
        fade time is a float. The EM score reels devices use this to set up the
        score controller that has to exist to manage them.

        You can safely delete this method if your device doesn't need it. (Most
        don't need it.)
        """
        pass

    def __init__(self, machine, name, config, collection=None, validate=True):
        self.log = logging.getLogger('YourNewDevice.' + name)
        super(YourNewDevice, self).__init__(machine, name, config, collection,
                                            validate=validate)

    # Since this new device class is a subclass of Device and you're calling
    # super(), several attributes are available to you, including:

    # self.machine - a reference to the main machine controller object
    # self.name - a string of the name of this device ('device1', 'device2', etc.)
    # self.tags - any tags that were specified in the machine config files
    # self.label - a plain english description from the machine config files

    # Next, set config defaults

    # Typically you'd want to configure the default settings so your device
    # works even if the game programmer doesn't specify all the options for this
    # device in their machine configuration files.

    # For example:
    # if 'foo' not in self.config:
    #     self.config['foo'] = 'bar'

    # Finally, add the event handlers, methods, and attributes you need for your
    # new device.
