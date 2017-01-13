"""Config specs and validator."""
# pylint: disable-msg=too-many-lines
import logging
import re
from copy import deepcopy

from mpf._version import __version__
from mpf.core.rgb_color import named_rgb_colors, RGBColor
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.core.utility_functions import Util

from mpf.core.case_insensitive_dict import CaseInsensitiveDict

log = logging.getLogger('ConfigProcessor')

# values are type|validation|default
mpf_config_spec = '''

accelerometers:
    __valid_in__: machine
    platform: single|str|None
    hit_limits: single|float:str|None
    level_limits: single|float:str|None
    level_x: single|int|0
    level_y: single|int|0
    level_z: single|int|1
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
    number: single|str|
achievements:
    __valid_in__: mode
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
    enable_events: dict|str:ms|None
    start_events: dict|str:ms|None
    complete_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    stop_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    events_when_enabled: list|str|None
    events_when_started: list|str|None
    events_when_completed: list|str|None
    events_when_stopped: list|str|None
    events_when_disabled: list|str|None
    show_when_enabled: single|str|None
    show_when_started: single|str|None
    show_when_completed: single|str|None
    show_when_stopped: single|str|None
    show_when_disabled: single|str|None
    show_tokens: dict|str:str|None
    restart_on_next_ball_when_started: single|bool|True
    enable_on_next_ball_when_enabled: single|bool|True
    restart_after_stop_possible: single|bool|True
    start_enabled: single|bool|False
animations:
    __valid_in__: machine, mode                 # todo add to validator
assets:
    __valid_in__: machine, mode
    common:
        load: single|str|preload
        file: single|str|None
        priority: single|int|0
    images: # no image-specific config items
        __allow_others__:
    shows:  # no show-specific config items
        __allow_others__:
    sounds:
        __allow_others__:
    videos:
        width: single|num|None
        height: single|num|None
auditor:
    __valid_in__: machine
    save_events: list|str|ball_ended
    audit: list|str|None
    events: list|str|None
    player: list|str|None
    num_player_top_records: single|int|1
autofire_coils:
    __valid_in__: machine
    coil: single|machine(coils)|
    switch: single|machine(switches)|
    reverse_switch: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_ending
    coil_overwrite: dict|str:str|None
    switch_overwrite: dict|str:str|None

switch_overwrites:
    __valid_in__: machine
    debounce: single|enum(quick,normal,None)|None

coil_overwrites:
    __valid_in__: machine
    recycle: single|bool|None
    pulse_ms: single|ms|None
    pulse_power: single|int(0,8)|None
    hold_power: single|int(0,8)|None
fast_coil_overwrites:
    __valid_in__: machine
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    recycle_ms: single|ms|None
p_roc_coil_overwrites:
    __valid_in__: machine
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None

ball_devices:
    __valid_in__: machine
    exit_count_delay: single|ms|500ms
    entrance_count_delay: single|ms|500ms
    eject_coil: single|machine(coils)|None
    eject_coil_jam_pulse: single|ms|None
    eject_coil_retry_pulse: single|ms|None
    hold_coil: single|machine(coils)|None
    hold_coil_release_time: single|ms|1s
    hold_events: dict|str:ms|None
    hold_switches: list|machine(switches)|None
    entrance_switch: single|machine(switches)|None
    entrance_switch_full_timeout: single|ms|0
    entrance_events: dict|str:ms|None
    jam_switch: single|machine(switches)|None
    confirm_eject_type: single|enum(target,switch,event,fake)|target
    captures_from: single|machine(playfields)|playfield
    eject_targets: list|machine(ball_devices)|playfield
    eject_timeouts: list|ms|None
    ball_missing_timeouts: list|ms|None
    ball_missing_target: single|machine(playfields)|playfield
    confirm_eject_switch: single|machine(switches)|None
    confirm_eject_event: single|str|None
    max_eject_attempts: single|int|0
    ball_switches: list|machine(switches)|None
    ball_capacity: single|int|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    request_ball_events: list|str|None
    eject_events: dict|str:ms|None
    eject_all_events: dict|str:ms|None
    mechanical_eject: single|bool|False
    player_controlled_eject_event: single|str|None
    ball_search_order: single|int|100
    auto_fire_on_unexpected_ball: single|bool|True
    target_on_unexpected_ball: single|machine(ball_devices)|None
ball_locks:
    __valid_in__: machine, mode
    balls_to_lock: single|int|
    lock_devices: list|machine(ball_devices)|
    source_playfield: single|machine(ball_devices)|playfield
    request_new_balls_to_pf: single|bool|True
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting, ball_ending
    release_one_events: dict|str:ms|None
ball_saves:
    __valid_in__: machine, mode
    source_playfield: single|machine(ball_devices)|playfield
    active_time: single|ms|0
    hurry_up_time: single|ms|0
    grace_period: single|ms|0
    auto_launch: single|bool|True
    balls_to_save: single|int|1
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|ball_ending
    timer_start_events: dict|str:ms|None
bcp:
    __valid_in__: machine
    connections:
        host: single|str|None
        port: single|int|5050
coils:
    __valid_in__: machine
    number: single|str|
    pulse_ms: single|ms|None
    pulse_power: single|int(0,8)|None
    hold_power: single|int(0,8)|None
    recycle: single|bool|False
    allow_enable: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    pulse_events: dict|str:ms|None
    platform: single|str|None
dual_wound_coils:
    __valid_in__: machine
    main_coil: single|machine(coils)|
    hold_coil: single|machine(coils)|
    eos_switch: single|machine(switches)|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
opp_coils:
    __valid_in__: machine
    hold_power16: single|int|None
    recycle_factor: single|int|None
fast_coils:
    __valid_in__: machine
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    connection: single|enum(network,local,auto)|auto
    recycle_ms: single|ms|None
p_roc_coils:
    __valid_in__: machine
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None
coil_player:
    __valid_in__: machine, mode, show
    action: single|lstr|pulse
    # ms: single|ms|None
    power: single|float|1.0
    # pwm_on_ms: single|int|None
    # pwm_off_ms: single|int|None
    # pulse_power: single|int|None
    # hold_power: single|int|None
    # pulse_power32: single|int|None
    # hold_power32: single|int|None
    # pulse_pwm_mask: single|int|None
    # hold_pwm_mask: single|int|None
    __allow_others__:
color_correction_profile:
    __valid_in__: machine
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
config:
    __valid_in__: machine                           # todo add to validator
config_player_common:
    __valid_in__: None
    priority: single|int|0
control_events:  # subconfig for mode timers
    __valid_in__: None
    action: single|enum(add,subtract,jump,start,stop,reset,restart,pause,set_tick_interval,change_tick_interval)|
    event: single|str|
    value: single|int|None
credits:
    __valid_in__: machine
    max_credits: single|int|0
    free_play: single|bool|yes
    service_credits_switch: list|machine(switches)|None
    fractional_credit_expiration_time: single|ms|0
    credit_expiration_time: single|ms|0
    persist_credits_while_off_time: single|secs|1h
    free_play_string: single|str|FREE PLAY
    credits_string: single|str|CREDITS
    switches:
        switch: single|machine(switches)|None
        value: single|float|0.25
        type: single|str|money
    pricing_tiers:
        price: single|float|.50
        credits: single|int|1
displays:
    __valid_in__: machine
    width: single|int|800
    height: single|int|600
    default: single|bool|False
    fps: single|int|0
diverters:
    __valid_in__: machine
    activate_events: dict|str:ms|None
    activation_coil: single|machine(coils)|None
    activation_time: single|ms|0
    activation_switches: list|machine(switches)|None
    debug: single|bool|False
    deactivate_events: dict|str:ms|None
    deactivation_switches: list|machine(switches)|None
    deactivation_coil: single|machine(coils)|None
    disable_events: dict|str:ms|None
    disable_switches: list|machine(switches)|None
    enable_events: dict|str:ms|None
    feeder_devices: list|machine(ball_devices)|playfield
    label: single|str|%
    reset_events: dict|str:ms|machine_reset_phase_3
    tags: list|str|None
    targets_when_active: list|machine(ball_devices)|playfield
    targets_when_inactive: list|machine(ball_devices)|playfield
    type: single|enum(hold,pulse)|hold
diypinball:
    __valid_in__: machine
    debug: single|bool|False
    can_device: single|str|
drop_targets:
    __valid_in__: machine
    switch: single|machine(switches)|
    reset_coil: single|machine(coils)|None
    knockdown_coil: single|machine(coils)|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    reset_events: dict|str:ms|ball_starting, machine_reset_phase_3
    knockdown_events: dict|str:ms|None
    ball_search_order: single|int|100
drop_target_banks:
    __valid_in__: machine, mode
    drop_targets: list|machine(drop_targets)|
    reset_coil: single|machine(coils)|None
    reset_coils: list|machine(coils)|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
event_player:
    __valid_in__: machine, mode, show
    __allow_others__:
extra_balls:
    __valid_in__: mode
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    award_events: dict|str:ms|None
    reset_events: dict|str:ms|None
fadecandy:
    __valid_in__: machine
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
    keyframe_interpolation: single|bool|True
    dithering: single|bool|True
fast:
    __valid_in__: machine
    ports: list|str|
    baud: single|int|921600
    config_number_format: single|str|hex
    watchdog: single|ms|1000
    default_quick_debounce_open: single|ms|
    default_quick_debounce_close: single|ms|
    default_normal_debounce_open: single|ms|
    default_normal_debounce_close: single|ms|
    hardware_led_fade_time: single|ms|0
    debug: single|bool|False
file_shows:
    __valid_in__: machine, mode                      # todo add to validator
flasher_player:
    __valid_in__: machine, mode, show
    __allow_others__:
    ms: single|int|None
flashers:   # TODO: this should be a coil + x. actually extend coil config
    __valid_in__: machine
    number: single|str|
    flash_ms: single|ms|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    flash_events: dict|str:ms|None
    platform: single|str|None
    # driver settings
    pulse_ms: single|int|None
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None
    pulse_power: single|int|None
    hold_power: single|int|None
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    recycle: single|ms|None
flippers:
    __valid_in__: machine
    main_coil: single|machine(coils)|
    hold_coil: single|machine(coils)|None
    activation_switch: single|machine(switches)|
    eos_switch: single|machine(switches)|None
    use_eos: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_ending
    # enable_no_hold_events: dict|str:ms|None
    # invert_events: dict|str:ms|None
    main_coil_overwrite: dict|str:str|None
    hold_coil_overwrite: dict|str:str|None
    switch_overwrite: dict|str:str|None
    eos_switch_overwrite: dict|str:str|None
game:
    __valid_in__: machine
    balls_per_game: single|int|3
    max_players: single|int|4
    start_game_switch_tag: single|str|start
    add_player_switch_tag: single|str|start
    allow_start_with_loose_balls: single|bool|False
    allow_start_with_ball_in_drain: single|bool|False
gi_player:
    __valid_in__: machine, mode, show
    brightness: single|int_from_hex|ff
    __allow_others__:
gis:
    __valid_in__: machine
    number: single|str|
    dimmable: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|machine_reset_phase_3
    disable_events: dict|str:ms|None
    platform: single|str|None
    __allow_others__:
hardware:
    __valid_in__: machine
    platform: single|str|virtual
    coils: single|str|default
    switches: single|str|default
    matrix_lights: single|str|default
    leds: single|str|default
    dmd: single|str|default
    rgb_dmd: single|str|default
    gis: single|str|default
    flashers: single|str|default
    driverboards: single|str|
    servo_controllers: single|str|
    accelerometers: single|str|
    i2c: single|str|
high_score:
    __valid_in__: machine, mode
    award_slide_display_time: single|ms|4s
    categories: list|str:list|
    shift_left_tag: single|str|left_flipper
    shift_right_tag: single|str|right_flipper
    select_tag: single|str|start
info_lights:
    __valid_in__: machine                            # todo add to validator
image_pools:
    __valid_in__: machine, mode                      # todo add to validator
images:
    __valid_in__: machine, mode
    file: single|str|None
    load: single|str|None
keyboard:
    __valid_in__: machine                           # todo add to validator
kivy_config:
    __valid_in__: machine                           # todo add to validator
led_player:
    __valid_in__: machine, mode, show
    color: single|str|white
    fade: single|ms|0
    __allow_others__:
led_settings:
    __valid_in__: machine
    color_correction_profiles: single|dict|None
    default_color_correction_profile: single|str|None
    default_led_fade_ms: single|int|0
leds:
    __valid_in__: machine
    number: single|str|
    polarity: single|bool|False
    default_color: single|color|ffffff
    color_correction_profile: single|str|None
    fade_ms: single|ms|None
    tags: list|str|None
    type: single|lstr|rgb
    label: single|str|%
    debug: single|bool|False
    on_events:  dict|str:ms|None
    off_events:  dict|str:ms|None
    platform: single|str|None
    x: single|int|None
    y: single|int|None
    z: single|int|None
    # color_channel_map: single|str|rgb     # not implemented
light_player:
    __valid_in__: machine, mode, show
    brightness: single|int_from_hex|ff
    fade: single|ms|0
    __allow_others__:
logic_blocks:                                       # todo add validation
    __valid_in__: machine, mode
    common:
        enable_events: list|str|None
        disable_events: list|str|None
        reset_events: list|str|None
        restart_events: list|str|None
        reset_on_complete: single|bool|True
        disable_on_complete: single|bool|True
        persist_state: single|bool|False
        events_when_complete: list|str|None
        events_when_hit: list|str|None
        player_variable: single|str|None
    accrual:
        events: list|str|
    counter:
        count_events: list|str|
        count_complete_value: single|int|None
        multiple_hit_window: single|ms|0
        count_interval: single|int|1
        direction: single|str|up
        starting_count: single|int|0
    sequence:
        events: list|str|
machine:
    __valid_in__: machine
    balls_installed: single|int|1
    min_balls: single|int|1
matrix_light_settings:
    __valid_in__: machine
    default_light_fade_ms: single|int|0
matrix_lights:
    __valid_in__: machine
    number: single|str|
    tags: list|str|None
    label: single|str|%
    fade_ms: single|ms|None
    debug: single|bool|False
    on_events:  dict|str:ms|None
    off_events:  dict|str:ms|None
    platform: single|str|None
    x: single|int|None
    y: single|int|None
    z: single|int|None
mode:
    __valid_in__: mode
    priority: single|int|100
    start_events: list|str|None
    stop_events: list|str|None
    start_priority: single|int|0
    stop_priority: single|int|0
    use_wait_queue: single|bool|False
    code: single|str|None
    stop_on_ball_end: single|bool|True
    restart_on_next_ball: single|bool|False
mode_settings:
    __valid_in__: mode
    __allow_others__:
modes:
    __valid_in__: machine                           # todo add to validator
motors:
    __valid_in__: machine
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
    position_switches: dict|str:machine(switches)|
    reset_position: single|str|
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
    go_to_position: dict|str:str|None
    motor_coil: single|machine(coils)|
mpf:
    __valid_in__: machine                           # todo add to validator
    default_pulse_ms: single|int|10
    default_flash_ms: single|int|50
    auto_create_switch_events: single|bool|True
    switch_event_active: single|str|%_active
    switch_event_inactive: single|str|%_inactive
    switch_tag_event: single|str|sw_%
    allow_invalid_config_sections: single|bool|false
    save_machine_vars_to_disk: single|bool|true
    hz: single|float|30.0
mpf-mc:
    __valid_in__: machine                           # todo add to validator
multiballs:
    __valid_in__: machine, mode
    ball_count: single|int|
    source_playfield: single|machine(ball_devices)|playfield
    shoot_again: single|ms|10s
    ball_locks: list|machine(ball_locks)|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events:  dict|str:ms|None
    disable_events:  dict|str:ms|None
    reset_events:  dict|str:ms|machine_reset_phase_3, ball_starting
    start_events:  dict|str:ms|None
    stop_events:  dict|str:ms|None
opp:
    __valid_in__: machine
    ports: list|str|
    baud: single|int|115200
    debug: single|bool|False
osc:
    __valid_in__: machine
    client_port: single|int|8000
    debug_messages: single|bool|false
    machine_ip: single|str|auto
    machine_port: single|int|9000
    approved_client_ips: ignore
    client_updates: list|str|None
open_pixel_control:
    __valid_in__: machine
    connection_required: single|bool|False
    host: single|str|localhost
    port: single|str|7890
    connection_attempts: single|int|-1
    number_format: single|enum(int,hex)|int
    debug: single|bool|False
p_roc:
    __valid_in__: machine
    lamp_matrix_strobe_time: single|ms|100ms
    watchdog_time: single|ms|1s
    use_watchdog: single|bool|True
    dmd_timing_cycles: list|int|None
    dmd_update_interval: single|ms|33ms
    debug: single|bool|False
p3_roc:
    __valid_in__: machine
    lamp_matrix_strobe_time: single|ms|100ms
    watchdog_time: single|ms|1s
    use_watchdog: single|bool|True
    debug: single|bool|False
physical_dmd:
    __valid_in__: machine
    shades: single|pow2|16
    fps: single|int|30
    source_display: single|str|dmd
    luminosity: list|float|.299, .587, .114
    brightness: single|float|0.5
    only_send_changes: single|bool|False
physical_rgb_dmd:
    __valid_in__: machine
    fps: single|int|30
    source_display: single|str|dmd
    only_send_changes: single|bool|False
    brightness: single|float|1.0
playfields:
    __valid_in__: machine
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_ball_search: single|bool|False
    ball_search_timeout: single|ms|20s
    ball_search_interval: single|ms|250ms
    ball_search_phase_1_searches: single|int|3
    ball_search_phase_2_searches: single|int|3
    ball_search_phase_3_searches: single|int|4
    ball_search_failed_action: single|str|new_ball
    ball_search_wait_after_iteration: single|ms|10s
playfield_transfers:
    __valid_in__: machine
    ball_switch: single|machine(switches)|
    eject_target: single|machine(ball_devices)|
    captures_from: single|machine(ball_devices)|
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
plugins:
    __valid_in__: machine                      # todo add to validator
pololu_maestro:
    __valid_in__: machine
    port: single|str|
    servo_min: single|int|3000
    servo_max: single|int|9000
random_event_player:
    __valid_in__: machine, mode, show
    event_list: list|str|
score_reels:
    __valid_in__: machine
    coil_inc: single|machine(coils)|None
    rollover: single|bool|True
    limit_lo: single|int|0
    limit_hi: single|int|9
    repeat_pulse_time: single|ms|200
    hw_confirm_time: single|ms|300
    confirm: single|str|strict
    switch_0: single|machine(switches)|None
    switch_1: single|machine(switches)|None
    switch_2: single|machine(switches)|None
    switch_3: single|machine(switches)|None
    switch_4: single|machine(switches)|None
    switch_5: single|machine(switches)|None
    switch_6: single|machine(switches)|None
    switch_7: single|machine(switches)|None
    switch_8: single|machine(switches)|None
    switch_9: single|machine(switches)|None
    switch_10: single|machine(switches)|None
    switch_11: single|machine(switches)|None
    switch_12: single|machine(switches)|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
score_reel_groups:
    __valid_in__: machine
    max_simultaneous_coils: single|int|2
    reels: list|machine(score_reels)|
    chimes: list|machine(coils)|None
    repeat_pulse_time: single|ms|200
    hw_confirm_time: single|ms|300
    config: single|str|lazy
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    lights_tag: single|str|None
    confirm: single|str|lazy
scoring:
    __valid_in__: machine, modes                    # todo add to validator
scriptlets:
    __valid_in__: machine                           # todo add to validator
servo_controller:
    __valid_in__: machine                           # todo add to validator
servo_controllers:
    __valid_in__: machine
    platform: single|str|None
    address: single|int|64
    servo_min: single|int|150
    servo_max: single|int|600
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
servos:
    __valid_in__: machine
    positions: dict|float:str|None
    servo_min: single|float|0.0
    servo_max: single|float|1.0
    reset_position: single|float|0.5
    reset_events: dict|str:ms|ball_starting
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
    number: single|str|
    platform: single|str|None
shots:
    __valid_in__: machine, mode
    profile: single|str|None
    switch: list|machine(switches)|None
    switches: list|machine(switches)|None
    switch_sequence: list|machine(switches)|None
    cancel_switch: list|machine(switches)|None
    delay_switch: dict|machine(switches):ms|None
    time: single|ms|0
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    advance_events: dict|str:ms|None
    hit_events: dict|str:ms|None
    remove_active_profile_events: dict|str:ms|None
    show_tokens: dict|str:str|None
shot_groups:
    __valid_in__: machine, mode
    shots: list|machine(shots)|None
    profile: single|str|None    # TODO: convert from str to machine(profiles)
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    rotate_left_events: dict|str:ms|None
    rotate_right_events: dict|str:ms|None
    rotate_events: dict|str:ms|None
    enable_rotation_events: dict|str:ms|None
    disable_rotation_events: dict|str:ms|None
    advance_events: dict|str:ms|None
    remove_active_profile_events: dict|str:ms|None
shot_profiles:
    __valid_in__: machine, mode
    loop: single|bool|False
    show: single|str|None
    advance_on_hit: single|bool|True
    state_names_to_rotate: list|str|None
    state_names_to_not_rotate: list|str|None
    rotation_pattern: list|str|R
    player_variable: single|str|None
    show_when_disabled: single|bool|False
    block: single|bool|true
    states:
        show: single|str|None
        name: single|str|
        # These settings are same as show_player. Could probably get fancy with
        # the validator to make this automatically pull them in.
        action: single|enum(play,stop,pause,resume,advance,update)|play
        priority: single|int|0
        speed: single|float|1
        start_step: single|int|1
        loops: single|int|-1
        sync_ms: single|int|0
        reset: single|bool|True
        manual_advance: single|bool|False
        key: single|str|None
        show_tokens: dict|str:str|None
show_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,stop,pause,resume,advance,update)|play
    priority: single|int|0
    speed: single|float|1
    start_step: single|int|1
    loops: single|int|-1
    sync_ms: single|int|0
    reset: single|bool|True
    manual_advance: single|bool|False
    key: single|str|None
    show_tokens: dict|str:str|None
    __allow_others__:
show_pools:
    __valid_in__: machine, mode                      # todo add to validator

show_step:
    __valid_in__: None
    time: single|str|
    __allow_others__:
shows:
    __valid_in__: machine, mode                      # todo add to validator
slide_player:
    __valid_in__: machine, mode, show
    target: single|str|None
    priority: single|int|None                      # todo should this be 0?
    show: single|bool|True
    force: single|bool|False
    transition: ignore
    transition_out: ignore
    widgets: ignore
    expire: single|secs|None
    action: single|enum(play,remove)|play
    persist: single|bool|False                      # todo
slides:
    __valid_in__: machine, mode
    debug: single|bool|False
    tags: list|str|None
    expire: single|secs|None
    background_color: single|kivycolor|000000ff
    opacity: single|float|1.0
    transition_out: ignore
    __allow_others__:
snux:
    __valid_in__: machine
    flipper_enable_driver: single|machine(coils)|
    diag_led_driver: single|machine(coils)|
    platform: single|str|None
smartmatrix:
    __valid_in__: machine
    port: single|str|
    use_separate_thread: single|bool|true
sound_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,stop,stop_looping)|play
    volume: single|gain|None
    loops: single|int|None
    priority: single|int|None
    max_queue_time: single|secs|None
    __allow_others__:
sound_pools:
    __valid_in__: machine, mode                      # todo add to validator
sound_system:
    __valid_in__: machine
    enabled: single|bool|True
    buffer: single|int|2048
    frequency: single|int|44100
    channels: single|int|1
    master_volume: single|gain|0.5
    tracks: ignore                                  # todo add subconfig
sounds:
    __valid_in__: machine, mode
    file: single|str|None
    track: single|str|None
    volume: single|gain|0.5
    loops: single|int|0
    priority: single|int|0
    max_queue_time: single|secs|None
    events_when_played: list|str|None
    events_when_stopped: list|str|None
    events_when_looping: list|str|None
    ducking:
        target: single|str|
        delay: single|str|0
        attack: single|str|10ms
        attenuation: single|gain|1.0
        release_point: single|str|0
        release: single|str|10ms
switch_player:
    __valid_in__: machine
    start_event: single|str|machine_reset_phase_3
    steps: ignore
switches:
    __valid_in__: machine
    number: single|str|
    type: single|enum(NC,NO)|NO
    debounce: single|enum(auto,quick,normal)|auto
    ignore_window_ms: single|ms|0
    events_when_activated: list|str|None
    events_when_deactivated: list|str|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    platform: single|str|None
fast_switches:
    __valid_in__: machine
    debounce_open: single|str|None
    debounce_close: single|str|None
system11:
    __valid_in__: machine
    ac_relay_delay_ms: single|ms|75ms
    ac_relay_driver: single|machine(coils)|
text_strings:
    __valid_in__: machine, mode                 # todo add to validator
tilt:
    __valid_in__: machine, mode
    tilt_slam_tilt_events: list|str|None
    tilt_warning_events: list|str|None
    tilt_events: list|str|None
    tilt_warning_switch_tag: single|str|tilt_warning
    tilt_switch_tag: single|str|tilt
    slam_tilt_switch_tag: single|str|slam_tilt
    warnings_to_tilt: single|int|3
    reset_warnings_events: list|str|ball_ending
    multiple_hit_window: single|ms|300ms
    settle_time: single|ms|5s
    tilt_warnings_player_var: single|str|tilt_warnings
timers:
    __valid_in__: mode
    debug: single|bool|False
    start_value: single|int|0
    end_value: single|int|None
    direction: single|str|up
    max_value: single|ms|None
    tick_interval: single|ms|1s
    start_running: single|bool|False
    control_events: list|subconfig(control_events)|None
    restart_on_complete: single|bool|False
    bcp: single|bool|False
transitions:
    __valid_in__: None
    push:
        type: single|str|
        direction: single|str|left
        easing: single|str|out_quad
        duration: single|secs|1
    move_in:
        type: single|str|
        direction: single|str|left
        easing: single|str|out_quad
        duration: single|secs|1
    move_out:
        type: single|str|
        direction: single|str|left
        easing: single|str|out_quad
        duration: single|secs|1
    fade:
        type: single|str|
        duration: single|secs|1
    swap:
        type: single|str|
        duration: single|secs|2
    wipe:
        type: single|str|
    fade_back:
        type: single|str|
        duration: single|secs|2
    rise_in:
        type: single|str|
        duration: single|secs|2
    none:
        type: ignore

    # clearcolor
    # fs
    # vs
trigger_player:                                    # todo
    __valid_in__: machine, mode, show
    __allow_others__:
video_pools:
    __valid_in__: machine, mode                      # todo add to validator
videos:
    __valid_in__: machine, mode
    file: single|str|None
    load: single|str|None
    auto_play: single|bool|True
virtual_platform_start_active_switches:
    __valid_in__: machine                           # todo add to validator
widget_player:
    __valid_in__: machine, mode, show
    target: single|str|None
    slide: single|str|None
    action: single|enum(add,remove,update)|add
    key: single|str|None
    widget_settings: ignore
widget_styles:
    __valid_in__: machine, mode, show
    color: single|kivycolor|ffffffff
    __allow_others__:
widgets:
    __valid_in__: machine, mode
    common:
        type: single|str|slide_frame
        x: single|str|None
        y: single|str|None
        anchor_x: single|str|None
        anchor_y: single|str|None
        opacity: single|float|1.0
        z: single|int|0
        animations: ignore
        reset_animations_events: list|str|None
        color: single|kivycolor|ffffffff
        style: single|str|None
        adjust_top: single|int|None
        adjust_bottom: single|int|None
        adjust_left: single|int|None
        adjust_right: single|int|None
        expire: single|secs|None
        key: single|str|None
    animations:
        property: list|str|
        value: list|str|
        duration: single|secs|1
        timing: single|str|after_previous
        repeat: single|bool|False
        easing: single|str|linear
    bezier:
        points: list|num|
        thickness: single|float|1.0
        cap: single|str|round
        joint: single|str|round
        cap_precision: single|int|10
        joint_precision: single|int|10
        close: single|bool|False
        precision: single|int|180
    color_dmd:
        width: single|num|
        height: single|num|
        source_display: single|str|dmd
        gain: single|float|1.0
        pixel_color: single|kivycolor|None
        dark_color: single|kivycolor|221100
        shades: single|int|0
        bg_color: single|kivycolor|191919ff
        blur: single|float|0.1
        pixel_size: single|float|0.5
        dot_filter: single|bool|True
    dmd:
        width: single|num|
        height: single|num|
        source_display: single|str|dmd
        luminosity: list|float|.299, .587, .114
        gain: single|float|1.0
        pixel_color: single|kivycolor|ff5500  # classic DMD orange
        dark_color: single|kivycolor|221100
        shades: single|int|16
        bg_color: single|kivycolor|191919ff
        blur: single|float|0.1
        pixel_size: single|float|0.5
        dot_filter: single|bool|True
    ellipse:
        width: single|num|
        height: single|num|
        segments: single|int|180
        angle_start: single|int|0
        angle_end: single|int|360
    image:
        allow_stretch: single|bool|False
        fps: single|int|10
        loops: single|int|0
        keep_ratio: single|bool|False
        image: single|str|
        height: single|int|0
        width: single|int|0
        auto_play: single|bool|True
        start_frame: single|int|0                          # todo
    line:
        points: list|num|
        thickness: single|float|1.0
        cap: single|str|round
        joint: single|str|round
        cap_precision: single|int|10
        joint_precision: single|int|10
        close: single|bool|False
    points:
        points: list|num|
        size: single|float|1.0
    quad:
        points: list|num|
    rectangle:
        width: single|float|
        height: single|float|
        corner_radius: single|int|0
        corner_segments: single|int|10
    slide_frame:
        name: single|str|
        width: single|int|
        height: single|int|
    text:
        text: single|str|
        font_size: single|num|15
        font_name: ignore
        bold: single|bool|False
        italic: single|bool|False
        number_grouping: single|bool|True
        min_digits: single|int|1
        halign: single|str|center
        valign: single|str|middle
        # text_size: single|int|None  # sets width of bounding box, not font
        # shorten: single|bool|None
        # mipmap: single|bool|None
        # markup: single|bool|None
        # line_height: single|float|None
        # max_lines: single|int|None
        # strip: single|bool|None
        # shorten_from: single|str|None
        # split_str: single|str|None
        # unicode_errors: single|str|None
        # antialias: single|bool|False      # todo
    text_input:
        key: single|str|
        initial_char: single|str|A
        font_size: single|num|15
        font_name: ignore
        halign: single|str|center
        valign: single|str|middle
        shift_left_event: single|str|sw_left_flipper
        shift_right_event: single|str|sw_right_flipper
        select_event: single|str|sw_start
        abort_event: single|str|sw_esc
        force_complete_event: single|str|None
        bold: single|bool|False
        italic: single|bool|False
        max_chars: single|int|3
        char_list: single|str|"ABCDEFGHIJKLMNOPQRSTUVWXYZ_- "
        keep_selected_char: single|bool|True
        dynamic_x: single|bool|True
        dynamic_x_pad: single|int|0
        number_grouping: single|bool|False
        min_digits: single|int|0
    triangle:
        points: list|num|
    video:
        video: single|str|
        height: single|int|0
        width: single|int|0
        volume: single|float|1.0
        auto_play: single|bool|True
        end_behavior: single|enum(loop,pause,stop)|stop
        control_events: list|subconfig(video_control_events)|None

video_control_events:
    __valid_in__: None
    action: single|enum(play,pause,stop,seek,volume,position)|
    event: single|str|
    value: single|float|None

window:
    __valid_in__: machine
    icon: single|str|None
    title: single|str|Mission Pinball Framework v{}
    source_display: single|str|default
    borderless: single|bool_int|0
    resizable: single|bool_int|1
    fullscreen: single|bool_int|0
    show_cursor: single|bool_int|1
    exit_on_escape: single|bool|true
    height: single|int|600
    maxfps: single|int|60
    width: single|int|800
    minimum_width: single|int|0
    minimum_height: single|int|0
    left: single|int|None
    top: single|int|None
    no_window: single|bool|False
'''.format(__version__)


class ConfigValidator(object):
    config_spec = None

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('ConfigProcessor')

        self.validator_list = {
            "str": self._validate_type_str,
            "lstr": self._validate_type_lstr,
            "float": self._validate_type_float,
            "int": self._validate_type_int,
            "num": self._validate_type_num,
            "bool": self._validate_type_bool,
            "boolean": self._validate_type_bool,
            "ms": self._validate_type_ms,
            "secs": self._validate_type_secs,
            "list": self._validate_type_list,
            "int_from_hex": self._validate_type_int_from_hex,
            "dict": self._validate_type_dict,
            "kivycolor": self._validate_type_kivycolor,
            "color": self._validate_type_color,
            "bool_int": self._validate_type_bool_int,
            "pow2": self._validate_type_pow2,
            "gain": self._validate_type_gain,
            "subconfig": self._validate_type_subconfig,
            "enum": self._validate_type_enum,
            "machine": self._validate_type_machine,
        }

        if not ConfigValidator.config_spec:
            ConfigValidator.load_config_spec()

    @classmethod
    def load_config_spec(cls, config_spec=None):
        if not config_spec:
            config_spec = mpf_config_spec

        cls.config_spec = YamlInterface.process(config_spec)

    @classmethod
    def unload_config_spec(cls):
        # cls.config_spec = None
        pass

        # todo I had the idea that we could unload the config spec to save
        # memory, but doing so will take more thought about timing

    def _build_spec(self, config_spec, base_spec):
        if not self.config_spec:
            self.load_config_spec()

        # build up the actual config spec we're going to use
        spec_list = [config_spec]

        if base_spec:
            if isinstance(base_spec, list):
                spec_list.extend(base_spec)
            else:
                spec_list.append(base_spec)

        this_spec = dict()
        for spec_element in spec_list:
            this_base_spec = self.config_spec
            spec_element = spec_element.split(':')
            for spec in spec_element:
                # need to deepcopy so the orig base spec doesn't get polluted
                # with this widget's spec
                this_base_spec = deepcopy(this_base_spec[spec])

            this_base_spec.update(this_spec)
            this_spec = this_base_spec

        return this_spec

    # pylint: disable-msg=too-many-arguments
    def validate_config(self, config_spec, source, section_name=None,
                        base_spec=None, add_missing_keys=True):
        # config_spec, str i.e. "device:shot"
        # source is dict
        # section_name is str used for logging failures

        if source is None:
            source = CaseInsensitiveDict()

        if not section_name:
            section_name = config_spec  # str

        validation_failure_info = (config_spec, section_name)

        this_spec = self._build_spec(config_spec, base_spec)

        if '__allow_others__' not in this_spec:
            self.check_for_invalid_sections(this_spec, source,
                                            validation_failure_info)

        processed_config = source

        if not isinstance(source, (list, dict)):
            self.validation_error("", validation_failure_info, "Source should be list or dict but is {}".format(
                source.__class__
            ))

        for k in list(this_spec.keys()):
            if this_spec[k] == 'ignore' or k[0] == '_':
                continue

            elif k in source:  # validate the entry that exists

                if isinstance(this_spec[k], dict):
                    # This means we're looking for a list of dicts

                    final_list = list()
                    if k in source:
                        for i in source[k]:  # individual step
                            final_list.append(self.validate_config(
                                config_spec + ':' + k, source=i,
                                section_name=k))

                    processed_config[k] = final_list

                else:
                    processed_config[k] = self.validate_config_item(
                        this_spec[k], item=source[k],
                        validation_failure_info=(validation_failure_info, k))

            elif add_missing_keys:  # create the default entry

                if isinstance(this_spec[k], dict):
                    processed_config[k] = list()

                else:
                    processed_config[k] = self.validate_config_item(
                        this_spec[k],
                        validation_failure_info=(
                            validation_failure_info, k))

        return processed_config

    def validate_config_item(self, spec, validation_failure_info,
                             item='item not in config!@#', ):

        try:
            item_type, validation, default = spec.split('|')
        except (ValueError, AttributeError):
            raise ValueError('Error in validator spec: {}:{}'.format(
                validation_failure_info, spec))

        if default.lower() == 'none':
            default = None
        elif not default:
            default = 'default required!@#'

        if item == 'item not in config!@#':
            if default == 'default required!@#':
                raise ValueError('Required setting missing from config file. '
                                 'Run with verbose logging and look for the last '
                                 'ConfigProcessor entry above this line to see where the '
                                 'problem is. {} {}'.format(spec,
                                                            validation_failure_info))
            else:
                item = default

        if item_type == 'single':
            return self.validate_item(item, validation,
                                      validation_failure_info)

        elif item_type == 'list':
            item_list = Util.string_to_list(item)

            new_list = list()

            for i in item_list:
                new_list.append(self.validate_item(i, validation, validation_failure_info))

            return new_list

        elif item_type == 'set':
            item_set = set(Util.string_to_list(item))

            new_set = set()

            for i in item_set:
                new_set.add(self.validate_item(i, validation, validation_failure_info))

            return new_set

        elif item_type == 'dict':
            item_dict = self.validate_item(item, validation,
                                           validation_failure_info)

            if not item_dict:
                return dict()
            else:
                return item_dict

        else:
            raise AssertionError("Invalid Type '{}' in config spec {}:{}".format(item_type,
                                 validation_failure_info[0][0],
                                 validation_failure_info[1]))

    def check_for_invalid_sections(self, spec, config,
                                   validation_failure_info):

        for k in config:
            if not isinstance(k, dict):
                if k not in spec and k[0] != '_':

                    path_list = validation_failure_info[0].split(':')

                    if len(path_list) > 1 and path_list[-1] == validation_failure_info[1]:
                        path_list.append('[list_item]')
                    elif path_list[0] == validation_failure_info[1]:
                        path_list = list()

                    path_list.append(validation_failure_info[1])
                    path_list.append(k)

                    path_string = ':'.join(path_list)

                    if self.machine.machine_config['mpf']['allow_invalid_config_sections']:

                        self.log.warning('Unrecognized config setting. "%s" is '
                                         'not a valid setting name.',
                                         path_string)

                    else:
                        self.log.error('Your config contains a value for the '
                                       'setting "%s", but this is not a valid '
                                       'setting name.', path_string)

                        raise AssertionError('Your config contains a value for the '
                                             'setting "' + path_string + '", but this is not a valid '
                                                                         'setting name.')

    def _validate_type_subconfig(self, item, param, validation_failure_info):
        del validation_failure_info
        return self.validate_config(param, item)

    def _validate_type_enum(self, item, param, validation_failure_info):
        enum_values = param.lower().split(",")

        try:
            item = item.lower()
        except AttributeError:
            pass

        if item is None and "none" in enum_values:
            return None
        elif item in enum_values:
            return item

        elif item is False and 'no' in enum_values:
            return 'no'

        elif item is True and 'yes' in enum_values:
            return 'yes'

        else:
            self.validation_error(item, validation_failure_info,
                                  "Entry \"{}\" is not valid for enum. Valid values are: {}".format(
                                      item,
                                      str(param)
                                  ))

    def _validate_type_machine(self, item, param, validation_failure_info):
        if item is None:
            return None

        section = getattr(self.machine, param, [])

        if item in section:
            return section[item]
        else:
            self.validation_error(item, validation_failure_info)

    @classmethod
    def _validate_type_list(cls, item, validation_failure_info):
        del validation_failure_info
        return Util.string_to_list(item)

    @classmethod
    def _validate_type_int_from_hex(cls, item, validation_failure_info):
        del validation_failure_info
        return Util.hex_string_to_int(item)

    @classmethod
    def _validate_type_gain(cls, item, validation_failure_info):
        del validation_failure_info
        return Util.string_to_gain(item)

    @classmethod
    def _validate_type_str(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return str(item)
        else:
            return None

    @classmethod
    def _validate_type_lstr(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return str(item).lower()
        else:
            return None

    def _validate_type_float(self, item, validation_failure_info):
        if item is None:
            return None
        try:
            return float(item)
        except (TypeError, ValueError):
            self.validation_error(item, validation_failure_info, "Could not convert to float")

    def _validate_type_int(self, item, validation_failure_info, param=None):
        if item is None:
            return None

        try:
            value = int(item)
        except (TypeError, ValueError):
            return self.validation_error(item, validation_failure_info, "Could not convert {} to int".format(item))

        if param:
            param = param.split(",")
            if param[0] != "NONE" and value < int(param[0]):
                self.validation_error(item, validation_failure_info, "{} is smaller then {}".format(item, param[0]))
            elif param[1] != "NONE" and value > int(param[1]):
                self.validation_error(item, validation_failure_info, "{} is larger then {}".format(item, param[0]))

        return value

    def _validate_type_num(self, item, validation_failure_info):
        if item is None:
            return None

        # used for int or float, but does not convert one to the other
        if isinstance(item, (int, float)):
            return item
        else:
            try:
                if '.' in item:
                    return float(item)
                else:
                    return int(item)
            except (TypeError, ValueError):
                self.validation_error(item, validation_failure_info, "Could not convert {} to num".format(item))

    @classmethod
    def _validate_type_bool(cls, item, validation_failure_info):
        del validation_failure_info
        if item is None:
            return None
        elif isinstance(item, str):
            return item.lower() not in ['false', 'f', 'no', 'disable', 'off']
        elif not item:
            return False
        else:
            return True

    @classmethod
    def _validate_type_ms(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return Util.string_to_ms(item)
        else:
            return None

    @classmethod
    def _validate_type_secs(cls, item, validation_failure_info):
        del validation_failure_info
        if item is not None:
            return Util.string_to_secs(item)
        else:
            return None

    @classmethod
    def _validate_type_dict(cls, item, validation_failure_info):
        del validation_failure_info
        return item

    @classmethod
    def _validate_type_kivycolor(cls, item, validation_failure_info):
        del validation_failure_info
        # Validate colors that will be used by Kivy. The result is a 4-item
        # list, RGBA, with individual values from 0.0 - 1.0
        if not item:
            return None

        color_string = str(item).lower()

        if color_string in named_rgb_colors:
            color = list(named_rgb_colors[color_string])

        elif Util.is_hex_string(color_string):
            color = [int(x, 16) for x in
                     re.split('([0-9a-f]{2})', color_string) if x != '']

        else:
            color = Util.string_to_list(color_string)

        for i, x in enumerate(color):
            color[i] = int(x) / 255

        if len(color) == 3:
            color.append(1)

        return color

    @classmethod
    def _validate_type_color(cls, item, validation_failure_info):
        del validation_failure_info
        # Validates colors by name, hex, or list, into a 3-item list, RGB,
        # with individual values from 0-255
        color_string = str(item).lower()

        if color_string in named_rgb_colors:
            return named_rgb_colors[color_string]
        elif Util.is_hex_string(color_string):
            return RGBColor.hex_to_rgb(color_string)

        else:
            color = Util.string_to_list(color_string)
            return int(color[0]), int(color[1]), int(color[2])

    def _validate_type_bool_int(self, item, validation_failure_info):
        if self._validate_type_bool(item, validation_failure_info):
            return 1
        else:
            return 0

    def _validate_type_pow2(self, item, validation_failure_info):
        if item is None:
            return None
        if not Util.is_power2(item):
            self.validation_error(item, validation_failure_info, "Could not convert {} to pow2".format(item))
        else:
            return item

    def validate_item(self, item, validator, validation_failure_info):

        try:
            if item.lower() == 'none':
                item = None
        except AttributeError:
            pass

        if ':' in validator:
            validator = validator.split(':')
            # item could be str, list, or list of dicts
            item = Util.event_config_to_dict(item)

            return_dict = dict()

            for k, v in item.items():
                return_dict[self.validate_item(k, validator[0],
                                               validation_failure_info)] = (
                    self.validate_item(v, validator[1],
                                       validation_failure_info)
                )

            return return_dict

        elif '(' in validator and ')' in validator[-1:] == ')':
            validator_parts = validator.split('(')
            validator = validator_parts[0]
            param = validator_parts[1][:-1]
            return self.validator_list[validator](item, validation_failure_info=validation_failure_info, param=param)
        elif validator in self.validator_list:
            return self.validator_list[validator](item, validation_failure_info=validation_failure_info)

        else:
            raise AssertionError("Invalid Validator '{}' in config spec {}:{}".format(
                                 validator,
                                 validation_failure_info[0][0],
                                 validation_failure_info[1]))

    @classmethod
    def validation_error(cls, item, validation_failure_info, msg=""):
        raise AssertionError("Config validation error: Entry {}:{}:{}:{} is not valid. {}".format(
            validation_failure_info[0][0],
            validation_failure_info[0][1],
            validation_failure_info[1],
            item, msg))
