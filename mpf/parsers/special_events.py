"""Special events for the docs."""


class SpecialEvents:

    """A class to document special events.

    This is a legacy thing until the docs parse mpfconfig.yaml to generate those or we find another way.
    """

    '''event: flipper_cancel

    desc: Posted when both flipper buttons are hit at the same time,
    useful as a "cancel" event for shows, the bonus mode, etc.

    Note that in order for this event to work, you have to add
    ``left_flipper`` as a tag to the switch for your left flipper,
    and ``right_flipper`` to your right flipper.

    See :doc:`/config/combo_switches` for details.
    '''

    '''event: flipper_cradle
    config_attribute: events_when_active

    desc: Posted when one of the flipper buttons has been active for 3
    seconds.

    Note that in order for this event to work, you have to add
    ``left_flipper`` as a tag to the switch for your left flipper,
    and ``right_flipper`` to your right flipper.

    See :doc:`/config/timed_switches` for details.
    '''

    '''event: flipper_cradle_release
    config_attribute: events_when_released

    desc: Posted when one of the flipper buttons that has previously
    been active for more than 3 seconds has been released.

    If the player pushes in one flipper button for more than 3 seconds,
    and then the second one and holds it in for more than 3 seconds,
    this event won't be posted until both buttons have been released.

    Note that in order for this event to work, you have to add
    ``left_flipper`` as a tag to the switch for your left flipper,
    and ``right_flipper`` to your right flipper.

    See :doc:`/config/timed_switches` for details.
    '''
