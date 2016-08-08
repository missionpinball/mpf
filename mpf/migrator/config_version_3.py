"""Migrate to config version 3."""

section_deprecations = '''
- max balls
- machine_flow
'''

section_warnings = '''
- path: shots
  url: "https://missionpinball.com/docs/configuration-file-reference/config-version-3/"
- path: drop_targets
  url: "https://missionpinball.com/docs/configuration-file-reference/config-version-3/"
- path: drop_target_banks
  url: "https://missionpinball.com/docs/configuration-file-reference/config-version-3/"
'''

section_replacements = '''
remove_profile_events: remove_active_profile_events
targets: shots
target_groups: shot_groups
target_profiles: shot_profiles
switch_activity: reverse_switch
log_color_changes: debug
attract_start: mode_attract_started
balls installed: balls_installed
min balls: min_balls
balls per game: balls_per_game
max players per game: max_players
steps: states
step_names_to_rotate: state_names_to_rotate
step_names_to_not_rotate: state_names_to_not_rotate
'''

string_replacements = '''
_remove_profile: _remove_active_profile
" target_group_": " shot_group_"
" target_": " shot_"
" targets_": " shots_"
'''
