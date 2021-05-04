"""Manager for segment display text transitions."""

from mpf.devices.segment_display.transitions import (PushTransition, CoverTransition,
                                                     UncoverTransition, WipeTransition, SplitTransition)


class TransitionManager:

    """Manages segment display text transitions."""

    def __init__(self, machine) -> None:
        """Initialize manager."""
        self.machine = machine
        self._transitions = dict()
        self._register_transitions()

    def register_transition(self, name, transition_cls):
        """Register a text transition."""
        self._transitions[name] = transition_cls

    def _register_transitions(self):
        """Register the built-in text transitions."""
        self.register_transition('push', PushTransition)
        self.register_transition('cover', CoverTransition)
        self.register_transition('uncover', UncoverTransition)
        self.register_transition('wipe', WipeTransition)
        self.register_transition('split', SplitTransition)

    def get_transition(self, output_length: int, collapse_dots: bool, collapse_commas: bool, transition_config=None):
        """Create a transition instance based on the specified configuration."""
        if transition_config:
            config = transition_config.copy()
            config.pop('type')
            return self._transitions[transition_config['type']](output_length, collapse_dots, collapse_commas, config)

        return None

    def validate_config(self, config):
        """Validate segment display transition config."""
        if 'transition' in config and config['transition']:
            if not isinstance(config['transition'], dict):
                config['transition'] = dict(type=config['transition'])

            try:
                config['transition'] = (
                    self.machine.config_validator.validate_config(
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
                    self.machine.config_validator.validate_config(
                        'segment_display_transitions:{}'.format(
                            config['transition_out']['type']),
                        config['transition_out']))

            except KeyError:
                raise ValueError('transition_out: section of config requires a "type:" setting')
        else:
            config['transition_out'] = None

        return config
