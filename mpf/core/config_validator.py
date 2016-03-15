import logging
import re
from copy import deepcopy

import ruamel.yaml as yaml

from mpf._version import __version__
from mpf.core.rgb_color import named_rgb_colors, RGBColor
from mpf.file_interfaces.yaml_interface import MpfLoader, YamlInterface
from mpf.core.utility_functions import Util

from mpf.core.case_insensitive_dict import CaseInsensitiveDict

log = logging.getLogger('ConfigProcessor')

# values are type|validation|default
mpf_config_spec = '''

accelerometers:
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
assets:
    common:
        load: single|str|preload
        file: single|str|None
        priority: single|int|0
    images: # no image-specific config items
    shows:  # no show-specific config items
    sounds: # no sound-specific config items
    videos:
        width: single|num|None
        height: single|num|None
auditor:
    save_events: list|str|ball_ended
    audit: list|str|None
    events: list|str|None
    player: list|str|None
    num_player_top_records: single|int|1
autofire_coils:
    coil: single|self.machine.coils[%]|
    switch: single|self.machine.switches[%]|
#    latch: single|bool|False
    reverse_switch: single|bool|False
    delay: single|int|0
    recycle_ms: single|int|125
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_ending
    # hw rules settings overrides
    pulse_ms: single|int|None
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None
    pulse_power: single|int|None
    hold_power: single|int|None
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    recycle_ms: single|int|None
    debounced: single|bool|False
    drive_now: single|bool|False
ball_devices:
    exit_count_delay: single|ms|500ms
    entrance_count_delay: single|ms|500ms
    eject_coil: single|self.machine.coils[%]|None
    eject_coil_jam_pulse: single|ms|None
    eject_coil_retry_pulse: single|ms|None
    hold_coil: single|self.machine.coils[%]|None
    hold_coil_release_time: single|ms|1s
    hold_events: dict|str:ms|None
    hold_switches: list|self.machine.switches[%]|None
    entrance_switch: single|self.machine.switches[%]|None
    entrance_events: dict|str:ms|None
    jam_switch: single|self.machine.switches[%]|None
    confirm_eject_type: single|str|target
    captures_from: single|self.machine.playfields[%]|playfield
    eject_targets: list|self.machine.ball_devices[%]|playfield
    eject_timeouts: list|ms|None
    ball_missing_timeouts: list|ms|None
    ball_missing_target: single|self.machine.playfields[%]|playfield
    confirm_eject_switch: single|self.machine.switches[%]|None
    confirm_eject_event: single|str|None
    max_eject_attempts: single|int|0
    ball_switches: list|self.machine.switches[%]|None
    ball_capacity: single|int|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    request_ball_events: list|str|None
    stop_events: dict|str:ms|None
    eject_events: dict|str:ms|None
    eject_all_events: dict|str:ms|None
    mechanical_eject: single|bool|False
    player_controlled_eject_event: single|str|None
    ball_search_order: single|int|100
    auto_fire_on_unexpected_ball: single|bool|True
ball_locks:
    balls_to_lock: single|int|
    lock_devices: list|self.machine.ball_devices[%]|
    source_playfield: single|self.machine.ball_devices[%]|playfield
    request_new_balls_to_pf: single|bool|True
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_ending
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting, ball_ending
    release_one_events: dict|str:ms|None
ball_saves:
    source_playfield: single|self.machine.ball_devices[%]|playfield
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
    connections:
        host: single|str|None
        port: single|int|5050
        connection_attempts: single|int|-1
        require_connection: single|bool|False
bcp_player:                                          # todo

coils:
    number: single|str|
    number_str: single|str|
    pulse_ms: single|int|None
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None
    pulse_power: single|int|None
    hold_power: single|int|None
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    recycle_ms: single|int|None
    allow_enable: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    pulse_events: dict|str:ms|None
    platform: single|str|None
coil_player:
    action: single|lstr|pulse
    ms: single|ms|None
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
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
config_player_common:
    priority: single|int|0
credits:
    max_credits: single|int|0
    free_play: single|bool|yes
    service_credits_switch: list|self.machine.switches[%]|None
    fractional_credit_expiration_time: single|ms|0
    credit_expiration_time: single|ms|0
    persist_credits_while_off_time: single|secs|1h
    free_play_string: single|str|FREE PLAY
    credits_string: single|str|CREDITS
    switches:
        switch: single|self.machine.switches[%]|None
        value: single|float|0.25
        type: single|str|money
    pricing_tiers:
        price: single|float|.50
        credits: single|int|1
displays:
    width: single|int|800
    height: single|int|600
    default: single|bool|False
    fps: single|int|0
diverters:
    type: single|str|hold
    activation_time: single|ms|0
    activation_switches: list|self.machine.switches[%]|None
    disable_switches: list|self.machine.switches[%]|None
    deactivation_switches: list|self.machine.switches[%]|None
    activation_coil: single|self.machine.coils[%]|None
    deactivation_coil: single|self.machine.coils[%]|None
    targets_when_active: list|self.machine.ball_devices[%]|playfield
    targets_when_inactive: list|self.machine.ball_devices[%]|playfield
    feeder_devices: list|self.machine.ball_devices[%]|playfield
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    activate_events: dict|str:ms|None
    deactivate_events: dict|str:ms|None
    # hw rules settings overrides
    pulse_ms: single|int|None
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None
    pulse_power: single|int|None
    hold_power: single|int|None
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    recycle_ms: single|int|None
    debounced: single|bool|False
    drive_now: single|bool|False
driver_enabled:
    number: single|str|
    number_str: single|str|
    allow_enable: single|bool|True
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    platform: single|str|None
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_ending
drop_targets:
    switch: single|self.machine.switches[%]|
    reset_coil: single|self.machine.coils[%]|None
    knockdown_coil: single|self.machine.coils[%]|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    reset_events: dict|str:ms|ball_starting, machine_reset_phase_3
    knockdown_events: dict|str:ms|None
    ball_search_order: single|int|100
drop_target_banks:
    drop_targets: list|self.machine.drop_targets[%]|
    reset_coil: single|self.machine.coils[%]|None
    reset_coils: list|self.machine.coils[%]|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
event_player:
    __allow_others__:
fadecandy:
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
    keyframe_interpolation: single|bool|True
    dithering: single|bool|True
fast:
    ports: list|str|
    baud: single|int|921600
    config_number_format: single|str|hex
    watchdog: single|ms|1000
    default_debounce_open: single|ms|30
    default_debounce_close: single|ms|30
    hardware_led_fade_time: single|ms|0
    debug: single|bool|False
flasher_player:
    __allow_others:
    ms: single|int|None
flashers:
    number: single|str|
    number_str: single|str|
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
    recycle_ms: single|int|None
flippers:
    main_coil: single|self.machine.coils[%]|
    hold_coil: single|self.machine.coils[%]|None
    activation_switch: single|self.machine.switches[%]|
    eos_switch: single|self.machine.switches[%]|None
    use_eos: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_ending
    enable_no_hold_events: dict|str:ms|None
    invert_events: dict|str:ms|None
    # hw rules settings overrides
    pulse_ms: single|int|None
    pwm_on_ms: single|int|None
    pwm_off_ms: single|int|None
    pulse_power: single|int|None
    hold_power: single|int|None
    pulse_power32: single|int|None
    hold_power32: single|int|None
    pulse_pwm_mask: single|int|None
    hold_pwm_mask: single|int|None
    recycle_ms: single|int|None
    debounced: single|bool|False
    drive_now: single|bool|False
game:
    balls_per_game: single|int|3
    max_players: single|int|4
    start_game_switch_tag: single|str|start
    add_player_switch_tag: single|str|start
    allow_start_with_loose_balls: single|bool|False
gi_player:
    brightness: single|int_from_hex|ff
    __allow_others__:
gis:
    number: single|str|
    number_str: single|str|
    dimmable: single|bool|False
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|machine_reset_phase_3
    disable_events: dict|str:ms|None
    platform: single|str|None
    __allow_others__:
hardware:
    platform: single|str|virtual
    coils: single|str|default
    switches: single|str|default
    matrix_lights: single|str|default
    leds: single|str|default
    dmd: single|str|default
    gis: single|str|default
    flashers: single|str|default
    driverboards: single|str|
    servo_controllers: single|str|
    accelerometers: single|str|
    i2c: single|str|
high_score:
    award_slide_display_time: single|ms|4s
    categories: list|str:list|
    shift_left_tag: single|str|left_flipper
    shift_right_tag: single|str|right_flipper
    select_tag: single|str|start
images:
    file: single|str|None
    load: single|str|None
led_player:
    color: single|str|white
    fade: single|ms|0
    force: single|bool|false
    __allow_others__:
led_settings:
    color_correction_profiles: single|dict|None
    default_color_correction_profile: single|str|None
    default_led_fade_ms: single|int|0
    brightness_compensation: ignore                              # todo
leds:
    number: single|str|
    number_str: single|str|
    polarity: single|bool|False
    default_color: single|color|ffffff
    color_correction_profile: single|str|None
    fade_ms: single|int|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    on_events:  dict|str:ms|None
    off_events:  dict|str:ms|None
    platform: single|str|None
    x: single|int|None
    y: single|int|None
    z: single|int|None
    color_channel_map: single|str|rgb
light_player:
    brightness: single|int_from_hex|ff
    fade_ms: single|ms|0
    force: single|bool|False
    __allow_others:
logic_block:
    common:
        enable_events: list|str|None
        disable_events: list|str|None
        reset_events: list|str|None
        restart_events: list|str|None
        reset_on_complete: single|bool|True
        disable_on_complete: single|bool|True
        persist_state: single|bool|False
        events_when_complete: list|str|None
        player_variable: single|str|None
    accrual:
        events: list|str|
    counter:
        count_events: list|str|
        count_complete_value: single|int|
        multiple_hit_window: single|ms|0
        count_interval: single|int|1
        direction: single|str|up
        starting_count: single|int|0
        event_when_hit: single|str|None
    sequence:
        events: list|str|
machine:
    balls_installed: single|int|1
    min_balls: single|int|1
    glass_off_mode: single|bool|True
matrix_lights:
    number: single|str|
    number_str: single|str|
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    on_events:  dict|str:ms|None
    off_events:  dict|str:ms|None
    platform: single|str|None
    x: single|int|None
    y: single|int|None
    z: single|int|None
mode:
    priority: single|int|100
    start_events: list|str|None
    stop_events: list|str|None
    start_priority: single|int|0
    stop_priority: single|int|0
    use_wait_queue: single|bool|False
    code: single|str|None
    stop_on_ball_end: single|bool|True
    restart_on_next_ball: single|bool|False
multiballs:
    ball_count: single|int|
    source_playfield: single|self.machine.ball_devices[%]|playfield
    shoot_again: single|ms|10s
    ball_locks: list|self.machine.ball_locks[%]|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events:  dict|str:ms|ball_started
    disable_events:  dict|str:ms|ball_ending
    reset_events:  dict|str:ms|machine_reset_phase_3, ball_starting
    start_events:  dict|str:ms|None
    stop_events:  dict|str:ms|None
osc:
    client_port: single|int|8000
    debug_messages: single|bool|false
    machine_ip: single|str|auto
    machine_port: single|int|9000
    approved_client_ips: ignore
    client_updates: list|str|None
physical_dmd:
    width: single|int|128
    height: single|int|32
    shades: single|pow2|16
    fps: single|int|0
    platform: single|str|None
    source_display: single|str|dmd
    luminosity: list|float|.299, .587, .114
    gain: single|float|1.0
physical_rgb_dmd:
    width: single|int|128
    height: single|int|32
    shades: single|pow2|16
    fps: single|int|0
    platform: single|str|None
    source_display: single|str|dmd
    color_adjust: list|float|1, 1, 1
    channel_bits: list|int|8, 8, 8
    color_channel_map: single|str|rgb
playfields:
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
    ball_switch: single|self.machine.switches[%]|
    eject_target: single|self.machine.ball_devices[%]|
    captures_from: single|self.machine.ball_devices[%]|
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
random_event_player:
    event_list: list|str|
score_reels:
    coil_inc: single|self.machine.coils[%]|None
    coil_dec: single|self.machine.coils[%]|None
    rollover: single|bool|True
    limit_lo: single|int|0
    limit_hi: single|int|9
    repeat_pulse_time: single|ms|200
    hw_confirm_time: single|ms|300
#    config: single|str|lazy
    confirm: single|str|strict
    switch_0: single|self.machine.switches[%]|None
    switch_1: single|self.machine.switches[%]|None
    switch_2: single|self.machine.switches[%]|None
    switch_3: single|self.machine.switches[%]|None
    switch_4: single|self.machine.switches[%]|None
    switch_5: single|self.machine.switches[%]|None
    switch_6: single|self.machine.switches[%]|None
    switch_7: single|self.machine.switches[%]|None
    switch_8: single|self.machine.switches[%]|None
    switch_9: single|self.machine.switches[%]|None
    switch_10: single|self.machine.switches[%]|None
    switch_11: single|self.machine.switches[%]|None
    switch_12: single|self.machine.switches[%]|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
score_reel_groups:
    max_simultaneous_coils: single|int|2
    reels: list|str|
    chimes: list|str|None
    repeat_pulse_time: single|ms|200
    hw_confirm_time: single|ms|300
    config: single|str|lazy
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    lights_tag: single|str|None
script_player:
    bcps: list|str|None
    coils: list|str|None
    displays: list|str|None
    events: list|str|None
    flashers: list|str|None
    gis: list|str|None
    leds: list|str|None
    lights: list|str|None
    random_events: list|str|None
    shows: list|str|None
    triggers: list|str|None
    script: single|str|
    action: single|str|play
    priority: single|int|0
    step_num: single|int|0
    loops: single|int|-1
    blend: single|bool|False
    speed: single|float|1
    key: single|str|None
scripts:
    time: ignore
    key: single|str|None
    loops: single|int|-1
    __allow_others__:
servo_controllers:
    platform: single|str|None
    address: single|int|64
    servo_min: single|int|150
    servo_max: single|int|600
    platform: single|str|None
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
servos:
    positions: dict|float:str|None
    servo_min: single|float|0.0
    servo_max: single|float|1.0
    reset_position: single|float|0.5
    reset_events: dict|str:ms|ball_starting
    debug: single|bool|False
    tags: list|str|None
    label: single|str|%
    number: single|int|
    platform: single|str|None
shots:
    profile: single|str|None
    switch: list|str|None
    switches: list|str|None
    switch_sequence: list|self.machine.switches[%]|None
    cancel_switch: list|self.machine.switches[%]|None
    delay_switch: dict|self.machine.switches[%]:ms|None
    time: single|ms|0
    # light: list|self.machine.lights[%]|None
    # led: list|self.machine.leds[%]|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    advance_events: dict|str:ms|None
    hit_events: dict|str:ms|None
    remove_active_profile_events: dict|str:ms|None
    __allow_others__:
shot_groups:
    shots: list|str|None
    profile: single|str|None
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
    loop: single|bool|False
    show: single|str|None
    state_names_to_rotate: list|str|None
    state_names_to_not_rotate: list|str|None
    rotation_pattern: list|str|R
    player_variable: single|str|None
    show_when_disabled: single|bool|True
    block: single|bool|true
    states:
        name: single|str|
        show: single|str|None
        hold: single|bool|True
        reset: single|bool|False
        repeat: single|bool|True
        blend: single|bool|False
        speed: single|float|1
        loops: single|int|0
        sync_ms:  single|int|0
        __allow_others__:
show_player:
    action: single|str|play
    repeat: single|bool|True
    step_num: single|int|0
    loops: single|int|-1
    blend: single|bool|False
    speed: single|float|1
    hold: single|bool|False
    __allow_others__:
show_step:
    time: single|str|
    __allow_others__:
slide_player:
    target: single|str|None
    priority: single|int|None
    show: single|bool|True
    force: single|bool|False
    transition: ignore
    widgets: ignore
    expire: single|secs|None                            # todo
slides:
    debug: single|bool|False
    tags: list|str|None
    __allow_others__:
snux:
    flipper_enable_driver_number: single|int|c23
    diag_led_driver_number: single|str|c24
smartmatrix:
    port: single|str|
    use_separate_thread: single|bool|true
sound_player:
    track: single|str|None
    volume: single|gain|None
    loops: single|int|None
    priority: single|int|None
    max_queue_time: single|secs|None
    __allow_others__:
sound_system:
    enabled: single|bool|True
    buffer: single|int|2048
    frequency: single|int|44100
    channels: single|int|1
    master_volume: single|gain|0.5
sounds:
    file: single|str|None
    track: single|str|None
    volume: single|gain|0.5
    loops: single|int|0
    priority: single|int|0
    max_queue_time: single|secs|None
    ducking:
        target: single|str|
        delay: single|str|0
        attack: single|str|10ms
        attenuation: single|gain|1.0
        release_point: single|str|0
        release: single|str|10ms
switches:
    number: single|str|
    number_str: single|str|
    type: single|str|NO
    debounce: single|bool|True
    recycle_time: single|secs|0
    events_when_activated: list|str|None
    events_when_deactivated: list|str|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    platform: single|str|None
    debounce_open: single|ms|None
    debounce_close: single|ms|None
system11:
    ac_relay_delay_ms: single|int|75
    ac_relay_driver_number: single|str|
text_styles:
    font_name: single|str|None
    font_size: single|num|None
    bold: single|bool|None
    italtic: single|bool|None
    halign: single|str|None
    valign: single|str|None
    padding_x: single|num|None
    padding_y: single|num|None
    # text_size: single||None
    shorten: single|bool|None
    mipmap: single|bool|None
    markup: single|bool|None
    line_height: single|float|None
    max_lines: single|int|None
    strip: single|bool|None
    shorten_from: single|str|None
    split_str: single|str|None
    unicode_errors: single|str|None
    color: single|kivycolor|ffffffff
    crop_top: single|int|0            # todo
    crop_bottom: single|int|0         # todo
    antialias: single|bool|False      # todo
tilt:
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
    debug: single|bool|False
    start_value: single|int|0
    end_value: single|int|None
    direction: single|str|up
    max_value: single|ms|None
    tick_interval: single|ms|1s
    start_running: single|bool|False
    control_events: ignore
    restart_on_complete: single|bool|False
    bcp: single|bool|False
transitions:
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
    __allow_others__:
videos:
    file: single|str|None
    load: single|str|None
    fps: single|num|None
    auto_play: single|bool|True
widgets:
    common:
        type: single|str|slide_frame
        x: single|str|None
        y: single|str|None
        anchor_x: single|str|None
        anchor_y: single|str|None
        opacity: single|float|1.0
        z: single|int|0
        animations: ignore
        color: single|kivycolor|ffffffff
        brightness: single|int|None
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
    character_picker:
        style: single|str|default
        name: single|str|
        selected_char_color: single|kivycolor|black
        selected_char_bg: single|kivycolor|white
        char_x_offset: single|int|1
        char_y_offset: single|int|1
        char_width: single|int|7
        char_list: single|str|"ABCDEFGHIJKLMNOPQRSTUVWXYZ_- "
        back_char: single|str|
        end_char: single|str|
        back_char_selected: single|str|
        end_char_selected: single|str|
        image_padding: single|int|1
        shift_left_tag: single|str|left_flipper
        shift_right_tag: single|str|right_flipper
        select_tag: single|str|start
        max_chars: single|int|3
        timeout: single|secs|30
        return_param: single|str|
        width: single|num|None
        height: single|num|None
        clear_slide: ignore                             # todo
        persist: ignore                                 # todo
        cursor_animations: ignore                       # todo
        slide_name: ignore                              # todo
    color_dmd:
        width: single|num|
        height: single|num|
        source_display: single|str|dmd
        gain: single|float|1.0
        pixel_color: single|kivycolor|None
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
    entered_chars:
        character_picker: single|str|
        cursor_char: single|str|_
        cursor_offset_x: single|int|0
        cursor_offset_y: single|int|0
        cursor_animations: ignore                         # todo
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
        x: single|float|None
        y: single|float|None
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
        halign: single|str|center
        valign: single|str|middle
        anchor_x: single|str|None
        anchor_y: single|str|None
        padding_x: single|int|0
        padding_y: single|int|0
        number_grouping: single|bool|True
        min_digits: single|int|1
        style: single|str|None
  #      text_size:
  #      shorten:
  #      mipmap:
  #      markup:
  #      line_height:
  #      max_lines:
  #      strip:
  #      shorten_from:
  #      split_str:
  #      unicode_errors:
    triangle:
        points: list|num|
    video:
        video: single|str|
        height: single|int|0
        width: single|int|0

widget_player:
    # widget: list|str|
    target: single|str|None
    slide: single|str|None

window:
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
        self.system_config = self.machine.get_system_config()

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

    @staticmethod
    def process_config(config_spec, source, target=None):  # pragma: no cover
        # Note this method is deprecated and will be removed eventually
        # Use process_config2() instead
        config_spec = yaml.load(config_spec, Loader=MpfLoader)
        processed_config = source

        for k in list(config_spec.keys()):
            if k in source:
                processed_config[k] = ConfigValidator.validate_config_item(
                        config_spec[k], source[k])
            else:
                log.debug('Processing default settings for key "%s:"', k)
                processed_config[k] = ConfigValidator.validate_config_item(
                        config_spec[k])

        if target:
            processed_config = Util.dict_merge(target, processed_config)

        return processed_config

    @staticmethod
    def validate_config_item(spec,
                             item='item not in config!@#'):  # pragma: no cover
        # Note this method is deprecated and will be removed eventually
        # Use validate_config_item2() instead

        try:
            if item.lower() == 'none':
                item = None
        except AttributeError:
            pass

        default = 'default required!@#'

        if '|' in spec:
            item_type, default = spec.split('|')
            if type(default) is str and default.lower() == 'none':
                default = None
        else:
            item_type = spec

        if item == 'item not in config!@#':
            if default == 'default required!@#':
                raise AssertionError('Required setting missing from config file. Run with '
                                     'verbose logging and look for the last '
                                     'ConfigProcessor entry above this line to see where '
                                     'the problem is.')
            else:
                item = default

        if item_type == 'list':
            return Util.string_to_list(item)

        if item_type == 'list_of_dicts':
            if type(item) is list:
                return item
            elif type(item) is dict:
                return [item]

        elif item_type == 'set':
            return set(Util.string_to_list(item))

        elif item_type == 'dict':
            if type(item) is dict or type(item) is CaseInsensitiveDict:
                return item
            elif not default:
                return dict()
            else:
                raise AssertionError('Config error. "{}" is not a dictionary'.format(item))

        elif item_type == 'int':
            try:
                return int(item)
            except TypeError:
                return None

        elif item_type == 'float':
            try:
                return float(item)
            except TypeError:
                return None

        elif item_type in ('string', 'str'):

            if item:
                return str(item)
            else:
                return None

        elif item_type in ('boolean', 'bool'):
            if type(item) is bool:
                return item
            else:
                return str(item).lower() in ('yes', 'true')

        elif item_type == 'ms':
            if item is None:
                return None
            else:
                return Util.string_to_ms(item)

        elif item_type == 'secs':
            if item is None:
                return None
            else:
                return Util.string_to_secs(item)

        elif item_type == 'list_of_lists':
            return Util.list_of_lists(item)

    def validate_config(self, config_spec, source=None, section_name=None,
                        target=None, result_type='dict', base_spec=None,
                        add_missing_keys=True):
        # config_spec, str i.e. "device:shot"
        # source is dict
        # section_name is str used for logging failures

        if not self.config_spec:
            self.load_config_spec()

        if source is None:
            source = CaseInsensitiveDict()

        if not section_name:
            section_name = config_spec  # str

        validation_failure_info = (config_spec, section_name)

        orig_spec = config_spec  # str

        # build up the actual config spec we're going to use
        this_spec = self.config_spec
        config_spec = config_spec.split(':')
        for i in range(len(config_spec)):
            this_spec = this_spec[config_spec[i]]

        if not isinstance(this_spec, dict):
            this_spec = dict()

        if base_spec:
            this_base_spec = self.config_spec
            base_spec = base_spec.split(':')
            for i in range(len(base_spec)):
                # need to deepcopy so the orig base spec doesn't get polluted
                # with this widget's spec
                this_base_spec = deepcopy(this_base_spec[base_spec[i]])

            this_base_spec.update(this_spec)
            this_spec = this_base_spec

        if '__allow_others__' not in this_spec:
            self.check_for_invalid_sections(this_spec, source,
                                            validation_failure_info)

        processed_config = source

        for k in list(this_spec.keys()):
            if this_spec[k] == 'ignore' or k[0] == '_':
                continue

            elif k in source:  # validate the entry that exists

                if type(this_spec[k]) is dict:
                    # This means we're looking for a list of dicts

                    final_list = list()
                    if k in source:
                        for i in source[k]:  # individual step
                            final_list.append(self.validate_config(
                                    orig_spec + ':' + k, source=i,
                                    section_name=k))

                    processed_config[k] = final_list

                elif result_type == 'list':
                    # spec is dict
                    # item is source
                    processed_config = self.validate_config_item2(
                            spec=this_spec[k], item=source[k],
                            validation_failure_info=(validation_failure_info, k))

                else:
                    processed_config[k] = self.validate_config_item2(
                            this_spec[k], item=source[k],
                            validation_failure_info=(validation_failure_info, k))

            elif add_missing_keys:  # create the default entry

                if type(this_spec[k]) is dict:
                    processed_config[k] = list()

                else:
                    if result_type == 'list':
                        processed_config = self.validate_config_item2(
                                this_spec[k],
                                validation_failure_info=(
                                    validation_failure_info, k))

                    else:
                        processed_config[k] = self.validate_config_item2(
                                this_spec[k],
                                validation_failure_info=(
                                    validation_failure_info, k))

        if target:
            processed_config = Util.dict_merge(target, processed_config)

        return processed_config

    def validate_config_item2(self, spec, validation_failure_info,
                              item='item not in config!@#', ):

        try:
            item_type, validation, default = spec.split('|')
        except ValueError:
            raise ValueError('Error in validator config: {}'.format(spec))

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
            item = self.validate_item(item, validation,
                                      validation_failure_info)

        elif item_type == 'list':
            item = Util.string_to_list(item)

            new_list = list()

            for i in item:
                new_list.append(
                        self.validate_item(i, validation,
                                           validation_failure_info))

            item = new_list

        elif item_type == 'set':
            item = set(Util.string_to_list(item))

            new_set = set()

            for i in item:
                new_set.add(
                        self.validate_item(i, validation,
                                           validation_failure_info))

            item = new_set

        elif item_type == 'dict':
            item = self.validate_item(item, validation,
                                      validation_failure_info)

            if not item:
                item = dict()

        else:
            raise AssertionError("Invalid Type '{}' in config spec {}:{}".format(item_type,
                                 validation_failure_info[0][0],
                                 validation_failure_info[1]))
        return item

    def check_for_invalid_sections(self, spec, config,
                                   validation_failure_info):

        for k in config:
            if type(k) is not dict:
                if k not in spec and k[0] != '_':

                    path_list = validation_failure_info[0].split(':')

                    if len(path_list) > 1 and (
                                path_list[-1] == validation_failure_info[1]):
                        path_list.append('[list_item]')
                    elif path_list[0] == validation_failure_info[1]:
                        path_list = list()

                    path_list.append(validation_failure_info[1])
                    path_list.append(k)

                    path_string = ':'.join(path_list)

                    if self.system_config['allow_invalid_config_sections']:

                        self.log.warning(
                                'Unrecognized config setting. "%s" is '
                                'not a valid setting name.',
                                path_string)

                    else:
                        self.log.error('Your config contains a value for the '
                                       'setting "%s", but this is not a valid '
                                       'setting name.', path_string)

                        raise AssertionError('Your config contains a value for the '
                                             'setting "' + path_string + '", but this is not a valid '
                                                                         'setting name.')

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

            item = return_dict

        elif '%' in validator:
            if type(item) is str:

                try:
                    item = eval(validator.replace('%', "'" + item + "'"))
                except KeyError:
                    self.validation_error(item, validation_failure_info)
            else:
                item = None

        elif validator == 'str':
            if item is not None:
                item = str(item)
            else:
                item = None

        elif validator == 'lstr':
            if item is not None:
                item = str(item).lower()
            else:
                item = None

        elif validator == 'float':
            try:
                item = float(item)
            except (TypeError, ValueError):
                # TODO error
                pass

        elif validator == 'int':
            try:
                item = int(item)
            except (TypeError, ValueError):
                pass

        elif validator == 'num':
            # used for int or float, but does not convert one to the other
            if type(item) not in (int, float):
                try:
                    if '.' in item:
                        item = float(item)
                    else:
                        item = int(item)
                except (TypeError, ValueError):
                    pass

        elif validator in ('bool', 'boolean'):
            if type(item) is str:
                if item.lower() in ['false', 'f', 'no', 'disable', 'off']:
                    item = False

            elif not item:
                item = False

            else:
                item = True

        elif validator == 'ms':
            if item is not None:
                item = Util.string_to_ms(item)

        elif validator == 'secs':
            if item is not None:
                item = Util.string_to_secs(item)

        elif validator == 'list':
            item = Util.string_to_list(item)

        elif validator == 'int_from_hex':
            item = Util.hex_string_to_int(item)

        elif validator == 'dict':
            return item

        elif validator == 'kivycolor':
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

        elif validator == 'color':
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

        elif validator == 'bool_int':
            if type(item) is str:
                if item.lower() in ('yes', 'true'):
                    return 1
                else:
                    return 0

            elif item:
                return 1
            else:
                return 0

        elif validator == 'pow2':
            if not Util.is_power2(item):
                raise ValueError
                # todo make a better error

        elif validator == 'gain':
            # Attenuation can be specified as a float value from 0.0 to 1.0 or as
            # a decibel level -inf to 0.0 (must be labeled as db)
            return Util.string_to_gain(item)

        else:
            raise AssertionError("Invalid Validator '{}' in config spec {}:{}".format(
                                 validator,
                                 validation_failure_info[0][0],
                                 validation_failure_info[1]))
        return item

    def validation_error(self, item, validation_failure_info):
        raise AssertionError(
                "Config validation error: Entry {}:{}:{}:{} is not valid".format(
                        validation_failure_info[0][0],
                        validation_failure_info[0][1],
                        validation_failure_info[1],
                        item))

