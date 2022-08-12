"""Manager for segment display text transitions."""

from mpf.devices.segment_display.transitions import (PushTransition, CoverTransition,
                                                     UncoverTransition, WipeTransition, SplitTransition)

TRANSITIONS = {
    "push": PushTransition,
    "cover": CoverTransition,
    "uncover": UncoverTransition,
    "wipe": WipeTransition,
    "split": SplitTransition
}


class TransitionManager:

    """Manages segment display text transitions."""

    __slots__ = []

    @staticmethod
    def get_transition(output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool,
                       transition_config=None):
        """Create a transition instance based on the specified configuration."""
        if transition_config:
            config = transition_config.copy()
            config.pop('type')
            return TRANSITIONS[transition_config['type']](output_length, collapse_dots, collapse_commas, 
                               use_dots_for_commas, config)

        return None

    @staticmethod
    def validate_config(config, config_validator):
        """Validate segment display transition config."""
        if 'transition' in config and config['transition']:
            if not isinstance(config['transition'], dict):
                config['transition'] = dict(type=config['transition'])

            try:
                config['transition'] = (
                    config_validator.validate_config(
                        'segment_display_transitions:{}'.format(config['transition']['type']),
                        config['transition']))

            except KeyError:
                raise ValueError('transition: section of config requires a "type:" setting')
        else:
            config['transition'] = None

        if 'transition_out' in config and config['transition_out']:
            if not isinstance(config['transition_out'], dict):
                config['transition_out'] = dict(type=config['transition_out'])

            try:
                config['transition_out'] = (
                    config_validator.validate_config(
                        'segment_display_transitions:{}'.format(
                            config['transition_out']['type']),
                        config['transition_out']))

            except KeyError:
                raise ValueError('transition_out: section of config requires a "type:" setting')
        else:
            config['transition_out'] = None

        return config
