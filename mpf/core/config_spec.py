# pylint: disable-msg=too-many-lines
"""Config spec for MPF."""
from mpf._version import __version__

# values are type|validation|default
mpf_config_spec = '''

accelerometers:
    __valid_in__: machine
    platform: single|str|None
    hit_limits: dict|float:str|None
    level_limits: dict|float:str|None
    level_x: single|int|0
    level_y: single|int|0
    level_z: single|int|1
    alpha: single|float|0.8
    platform_settings: dict|str:str|None
achievement_groups:
    __valid_in__: mode
    achievements: list|machine(achievements)|
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    start_selected_events: dict|str:ms|None
    select_random_achievement_events: dict|str:ms|None
    allow_selection_change_while_disabled: single|bool|False
    auto_select: single|bool|False
    disable_while_achievement_started: single|bool|True
    enable_while_no_achievement_started: single|bool|True
    rotate_right_events: dict|str:ms|None
    rotate_left_events: dict|str:ms|None
    events_when_all_completed: list|str|None
    events_when_no_more_enabled: list|str|None
    events_when_enabled: list|str|None
    show_tokens: dict|str:str|None
    show_when_enabled: single|str|None
achievements:
    __valid_in__: mode
    show_tokens: dict|str:str|None
    restart_after_stop_possible: single|bool|True
    restart_on_next_ball_when_started: single|bool|False
    enable_on_next_ball_when_enabled: single|bool|True

    enable_events: dict|str:ms|None
    start_events: dict|str:ms|None
    complete_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    stop_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    select_events: dict|str:ms|None

    events_when_enabled: list|str|None
    events_when_started: list|str|None
    events_when_completed: list|str|None
    events_when_stopped: list|str|None
    events_when_disabled: list|str|None
    events_when_selected: list|str|None

    show_when_enabled: single|str|None
    show_when_started: single|str|None
    show_when_completed: single|str|None
    show_when_stopped: single|str|None
    show_when_disabled: single|str|None
    show_when_selected: single|str|None
    sync_ms: single|int|None

animations:
    __valid_in__: machine, mode                 # todo add to validator
assets:
    __valid_in__: machine, mode
    common:
        load: single|str|preload
        file: single|str|None
        priority: single|int|0
    bitmap_fonts:
        descriptor: ignore
    images: # no image-specific config items
        __allow_others__:
    shows:  # no show-specific config items
        __allow_others__:
    sounds:
        __allow_others__:
    videos:
        width: single|num|None
        height: single|num|None
        events_when_played: list|str|None
        events_when_stopped: list|str|None
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
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_will_end, service_mode_entered
    coil_overwrite: single|subconfig(coil_overwrites)|None
    switch_overwrite: dict|str:str|None
    ball_search_order: single|int|100
    playfield: single|machine(playfields)|playfield
    timeout_watch_time: single|ms|0
    timeout_max_hits: single|int|0
    timeout_disable_time: single|ms|0
coil_overwrites:
    __valid_in__: machine
    recycle: single|bool|None
    pulse_ms: single|ms|None
    pulse_power: single|float(0,1)|None
    hold_power: single|float(0,1)|None
ball_devices:
    __valid_in__: machine
    exit_count_delay: single|ms|500ms
    entrance_count_delay: single|ms|500ms
    eject_coil: single|machine(coils)|None
    eject_coil_jam_pulse: single|ms|None
    eject_coil_retry_pulse: single|ms|None
    eject_coil_reorder_pulse: single|ms|None
    eject_coil_max_wait_ms: single|ms|200ms
    eject_coil_enable_time: list|ms|None
    retries_before_increasing_pulse: single|int|4
    hold_coil: single|machine(coils)|None
    hold_coil_release_time: single|ms|1s
    hold_events: dict|str:ms|None
    hold_switches: list|machine(switches)|None
    entrance_switch: single|machine(switches)|None
    entrance_switch_full_timeout: single|ms|0
    entrance_events: dict|str:ms|None
    entrance_event_timeout: single|secs|5s
    idle_missing_ball_timeout: single|secs|5s
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
    request_ball_events: list|str|None
    eject_events: dict|str:ms|None
    eject_all_events: dict|str:ms|None
    mechanical_eject: single|bool|False
    player_controlled_eject_event: single|str|None
    ball_search_order: single|int|200
    auto_fire_on_unexpected_ball: single|bool|True
    target_on_unexpected_ball: single|machine(ball_devices)|None
    ejector: ignore
ball_devices_ejector_common:
    class: single|str|mpf.devices.ball_device.pulse_coil_ejector.PulseCoilEjector
ball_devices_ejector_event:
    class: ignore
    events_when_eject_try: list|str|None
    events_when_reoder_balls: list|str|None
    events_when_ball_search: list|str|None
ball_holds:
    __valid_in__: machine, mode
    balls_to_hold: single|int|None
    hold_devices: list|machine(ball_devices)|
    source_playfield: single|machine(ball_devices)|playfield
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting, ball_will_end, service_mode_entered
    release_one_events: dict|str:ms|None
    release_all_events: dict|str:ms|None
    release_one_if_full_events: dict|str:ms|None
ball_locks:
    __valid_in__: machine, mode
    balls_to_lock: single|int|
    lock_devices: list|machine(ball_devices)|
    source_playfield: single|machine(ball_devices)|playfield
    request_new_balls_to_pf: single|bool|True
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting, ball_will_end, service_mode_entered
    release_one_events: dict|str:ms|None
    release_one_if_full_events: dict|str:ms|None
ball_saves:
    __valid_in__: machine, mode
    source_playfield: single|machine(ball_devices)|playfield
    active_time: single|ms|0
    eject_delay: single|ms|0
    only_last_ball: single|bool|False
    hurry_up_time: single|ms|0
    grace_period: single|ms|0
    auto_launch: single|bool|True
    balls_to_save: single|int|1
    enable_events: dict|str:ms|None
    early_ball_save_events: dict|str:ms|None
    delayed_eject_events: dict|str:ms|None
    disable_events: dict|str:ms|ball_will_end, service_mode_entered
    timer_start_events: dict|str:ms|None
bcp:
    __valid_in__: machine
    debug: False
    connections:
        host: single|str|None
        port: single|int|5050
        type: single|str|
        required: single|bool|True
        exit_on_close: single|bool|True
    servers:
        ip: single|str|None
        port: single|int|5050
        type: single|str|
bitmap_fonts:
    __valid_in__: machine, mode
    file: single|str|None
    load: single|str|None
    descriptor: ignore
blocking:
    __valid_in__: mode
    __allow_others__:
bonus_mode_settings:
    display_delay_ms: single|ms|2000
    hurry_up_delay_ms: single|ms|500
    hurry_up_event: single|str|flipper_cancel
    end_bonus_event: single|str|None
    keep_multiplier: single|bool|False
    bonus_entries: list|subconfig(bonus_entries)|
bonus_entries:
    event: single|str|
    score: single|template_int|
    reset_player_score_entry: single|bool|False
    player_score_entry: single|str|None
    skip_if_zero: single|bool|True
coils:
    __valid_in__: machine
    allow_enable: single|bool|False
    number: single|str|
    default_recycle: single|bool|False
    default_pulse_ms: single|ms|None
    default_pulse_power: single|float(0,1)|None
    default_hold_power: single|float(0,1)|None
    max_pulse_ms: single|ms|None
    max_pulse_power: single|float(0,1)|1.0
    max_hold_power: single|float(0,1)|None
    disable_events: dict|str:ms|None
    enable_events: dict|str:ms|None
    pulse_events: dict|str:ms|None
    platform_settings: single|dict|None
    psu: single|machine(psus)|default
    platform: single|str|None
digital_outputs:
    __valid_in__: machine
    number: single|str|
    disable_events: dict|str:ms|None
    enable_events: dict|str:ms|None
    platform: single|str|None
    type: single|enum(light,driver)|
    light_subtype: single|str|None
dual_wound_coils:
    __valid_in__: machine
    main_coil: single|machine(coils)|
    hold_coil: single|machine(coils)|
    eos_switch: single|machine(switches)|None
opp_coils:
    __valid_in__: machine
    recycle_factor: single|int|None
fast_coils:
    __valid_in__: machine
    connection: single|enum(network,local,auto)|auto
    recycle_ms: single|ms|None
coil_player:
    __valid_in__: machine, mode, show
    action: single|lstr|pulse
    hold_power: single|float|None
    pulse_power: single|float|None
    pulse_ms: single|int|None
    max_wait_ms: single|int|None
color_correction_profile:
    __valid_in__: machine
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
combo_switches:
    __valid_in__: machine, mode
    tag_1: list|str|None
    tag_2: list|str|None
    switches_1: set|machine(switches)|None
    switches_2: set|machine(switches)|None
    max_offset_time: single|secs|-1
    hold_time: single|ms|0
    release_time: single|ms|0
    events_when_both: list|str|None
    events_when_inactive: list|str|None
    events_when_one: list|str|None
    events_when_switches_1: list|str|None
    events_when_switches_2: list|str|None
config:
    __valid_in__: machine, mode                           # todo add to validator
config_player_common:
    __valid_in__: None
    priority: single|int|0
credits:
    __valid_in__: machine
    max_credits: single|template_int|0
    free_play: single|bool|yes
    price_tier_template: single|str|{{credits}} CREDITS ${{price}}
    service_credits_switch: list|machine(switches)|None
    fractional_credit_expiration_time: single|ms|0
    credit_expiration_time: single|ms|0
    persist_credits_while_off_time: single|secs|1h
    free_play_string: single|str|FREE PLAY
    credits_string: single|str|CREDITS
    switches:
        switch: single|machine(switches)|None
        value: single|template_float|0.25
        type: single|str|money
    events:
        event: single|str|None
        credits: single|template_float|0.25
        type: single|str|replay
    pricing_tiers:
        price: single|template_float|.50
        credits: single|int|1
device:     # base for all devices
    __valid_in__: None
    label: single|str|%
    tags: list|str|None
    debug: single|bool|False
    console_log: single|enum(none,basic,full)|basic
    file_log: single|enum(none,basic,full)|basic
displays:
    __valid_in__: machine
    width: single|int|800
    height: single|int|600
    default: single|bool|False
    fps: single|int|0
    round_anchor_x: single|str|center
    round_anchor_y: single|str|middle
display_light_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,stop)|play
    lights: list|str|None
    bcp_connection: single|str|local_display
    min_x: single|int|0
    max_x: single|int|None
    min_y: single|int|0
    max_y: single|int|None
diverters:
    __valid_in__: machine
    activate_events: dict|str:ms|None
    activation_coil: single|machine(coils)|None
    activation_time: single|ms|0
    activation_switches: list|machine(switches)|None
    allow_multiple_concurrent_ejects_to_same_side: single|bool|True
    cool_down_time: single|ms|0
    deactivate_events: dict|str:ms|None
    deactivation_switches: list|machine(switches)|None
    deactivation_coil: single|machine(coils)|None
    disable_events: dict|str:ms|None
    disable_switches: list|machine(switches)|None
    enable_events: dict|str:ms|None
    feeder_devices: list|machine(ball_devices)|playfield
    reset_events: dict|str:ms|machine_reset_phase_3
    targets_when_active: list|machine(ball_devices)|playfield
    targets_when_inactive: list|machine(ball_devices)|playfield
    type: single|enum(hold,pulse)|hold
    ball_search_order: single|int|100
    ball_search_hold_time: single|ms|1s
    playfield: single|machine(playfields)|playfield
dmds:
    __valid_in__: machine
    platform: single|str|None
    shades: single|pow2|16
    fps: single|int|30
    source_display: single|str|dmd
    luminosity: list|float|.299, .587, .114
    brightness: single|float|1.0
    gamma: single|float|1.0
    only_send_changes: single|bool|False
drop_targets:
    __valid_in__: machine
    switch: single|machine(switches)|
    reset_coil: single|machine(coils)|None
    knockdown_coil: single|machine(coils)|None
    reset_events: dict|str:ms|ball_starting, machine_reset_phase_3
    knockdown_events: dict|str:ms|None
    enable_keep_up_events: dict|str:ms|None
    disable_keep_up_events: dict|str:ms|None
    ball_search_order: single|int|100
    reset_coil_max_wait_ms: single|ms|100ms
    knockdown_coil_max_wait_ms: single|ms|100ms
    ignore_switch_ms: single|ms|500ms
    playfield: single|machine(playfields)|playfield
drop_target_banks:
    __valid_in__: machine, mode
    drop_targets: list|machine(drop_targets)|
    reset_on_complete: single|ms|None
    reset_coil: single|machine(coils)|None
    reset_coils: list|machine(coils)|None
    reset_coil_max_wait_ms: single|ms|100ms
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
    ignore_switch_ms: single|ms|500ms
effects:
    __valid_in__: None
    common:
        type: single|str|
    anti_aliasing:
        none: ignore
    color_channel_mix:
        order: list|int|1, 2, 0
    color_dmd:
        dot_filter: single|bool|True
        dots_x: single|int|128
        dots_y: single|int|32
        blur: single|float|0.1
        dot_size: single|float|0.7
        background_color: single|kivycolor|191919ff
        gain: single|float|1.0
        shades: single|int|0
    colorize:
        tint_color: single|kivycolor|ff66ff00
    dmd:
        dot_filter: single|bool|True
        dots_x: single|int|128
        dots_y: single|int|32
        blur: single|float|0.1
        dot_size: single|float|0.7
        background_color: single|kivycolor|191919ff
        gain: single|float|1.0
        shades: single|int|16
        luminosity: list|float|.299, .587, .114
        dot_color: single|kivycolor|ff5500  # classic DMD orange
    dot_filter:
        dots_x: single|int|128
        dots_y: single|int|32
        blur: single|float|0.1
        dot_size: single|float|0.7
        background_color: single|kivycolor|191919ff
    flip_vertical:
        none: ignore
    gain:
        gain: single|float|1.0
    gamma:
        gamma: single|float|1.0
    horizontal_blur:
        size: single|float|4.0
    invert_colors:
        none: ignore
    monochrome:
        luminosity: list|float|.299, .587, .114
    pixelate:
        pixel_size: single|int|10
    reduce:
        shades: single|int|16
    scanlines:
        none: ignore
    vertical_blur:
        size: single|float|4.0
event_player:
    __valid_in__: machine, mode, show
    __allow_others__:
queue_event_player:
    __valid_in__: machine, mode
    args: dict|str:str|None
    queue_event: single|str|
    events_when_finished: single|str|None
queue_relay_player:
    __valid_in__: machine, mode
    args: dict|str:str|None
    post: single|str|
    wait_for: single|str|
    pass_args: single|bool|False
extra_balls:
    __valid_in__: mode
    enabled: single|bool|True
    group: single|machine(extra_ball_groups)|None
    award_events: dict|str:ms|None
    light_events: dict|str:ms|None
    max_per_game: single|int|1
extra_ball_groups:
    __valid_in__: machine
    enabled: single|bool|True
    award_events: dict|str:ms|None
    max_per_game: single|int|None
    max_per_ball: single|int|None
    max_lit: single|int|None
    lit_memory: single|bool|True
fadecandy:
    __valid_in__: machine
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
    keyframe_interpolation: single|bool|True
    dithering: single|bool|True
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
fast:
    __valid_in__: machine
    ports: list|str|
    baud: single|int|921600
    watchdog: single|ms|1000
    default_quick_debounce_open: single|ms|
    default_quick_debounce_close: single|ms|
    default_normal_debounce_open: single|ms|
    default_normal_debounce_close: single|ms|
    hardware_led_fade_time: single|ms|0
    debug: single|bool|False
    net_buffer: single|int|10
    rgb_buffer: single|int|3
    dmd_buffer: single|int|3
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
    firmware_updates: list|subconfig(fast_firmware_update)|None
fast_firmware_update:
    type: single|enum(net,rgb)|
    file: single|str|
    version: single|str|
file_shows:
    __valid_in__: machine, mode                      # todo add to validator
flasher_player:
    __valid_in__: machine, mode, show
    __allow_others__:
    ms: single|ms|100ms
flippers:
    __valid_in__: machine
    main_coil: single|machine(coils)|
    hold_coil: single|machine(coils)|None
    activation_switch: single|machine(switches)|None
    eos_switch: single|machine(switches)|None
    use_eos: single|bool|False
    enable_events: dict|str:ms|ball_started
    disable_events: dict|str:ms|ball_will_end, service_mode_entered
    sw_flip_events: dict|str:ms|None
    sw_release_events: dict|str:ms|None
    # enable_no_hold_events: dict|str:ms|None
    # invert_events: dict|str:ms|None
    main_coil_overwrite: single|subconfig(coil_overwrites)|None
    hold_coil_overwrite: single|subconfig(coil_overwrites)|None
    switch_overwrite: dict|str:str|None
    eos_switch_overwrite: dict|str:str|None
    power_setting_name: single|str|None
    include_in_ball_search: single|bool|False
    ball_search_order: single|int|100
    ball_search_hold_time: single|ms|1s
    playfield: single|machine(playfields)|playfield
game:
    __valid_in__: machine
    balls_per_game: single|template_int|3
    max_players: single|template_int|4
    start_game_switch_tag: single|str|start
    add_player_switch_tag: single|str|start
    allow_start_with_loose_balls: single|bool|False
    allow_start_with_ball_in_drain: single|bool|False
hardware:
    __valid_in__: machine
    platform: list|str|virtual
    coils: list|str|default
    segment_displays: list|str|default
    switches: list|str|default
    lights: list|str|default
    dmd: list|str|default
    rgb_dmd: list|str|default
    driverboards: single|str|
    servo_controllers: list|str|
    accelerometers: list|str|
    i2c: list|str|
    stepper_controllers: list|str|
    hardware_sound_system: list|str|default
hardware_sound_systems:
    __valid_in__: machine
    platform: single|str|None
hardware_sound_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,play_file,text_to_speech,set_volume,increase_volume,decrease_volume,stop)|play
    value: single|str|None
    platform_options: single|dict|None
    sound_system: single|machine(hardware_sound_systems)|default
high_score:
    __valid_in__: mode
    award_slide_display_time: single|ms|4s
    categories: omap|str:list|
    defaults: dict|str:list|None
    enter_initials_timeout: single|secs|20s
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
kickbacks:
    __valid_in__: machine
    coil: single|machine(coils)|
    switch: single|machine(switches)|
    reverse_switch: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|ball_will_end, service_mode_entered
    coil_overwrite: single|subconfig(coil_overwrites)|None
    switch_overwrite: dict|str:str|None
    ball_search_order: single|int|100
    playfield: single|machine(playfields)|playfield
    timeout_watch_time: single|ms|0
    timeout_max_hits: single|int|0
    timeout_disable_time: single|ms|0
kivy_config:
    __valid_in__: machine                           # todo add to validator
led_player:
    __valid_in__: machine, mode, show
    color: single|str|white
    fade: single|ms|None
    __allow_others__:
light_settings:
    __valid_in__: machine
    color_correction_profiles: single|dict|None
    default_color_correction_profile: single|str|None
    default_fade_ms: single|int|0
light_stripes:
    __valid_in__: machine
    number_start: single|int|
    number_template: single|str|None
    start_x: single|float|None
    start_y: single|float|None
    direction: single|float|None
    distance: single|float|None
    count: single|int|
    light_template: single|subconfig(lights,device)|
light_rings:
    __valid_in__: machine
    number_start: single|int|
    number_template: single|str|None
    center_x: single|float|None
    center_y: single|float|None
    start_angle: single|float|0
    radius: single|float|None
    count: single|int|
    light_template: single|subconfig(lights,device)|
lights:
    __valid_in__: machine
    number: single|str|None
    type: single|str|None
    subtype: single|str|None
    platform: single|str|None
    platform_settings: single|dict|None
    fade_ms: single|ms|None
    color_correction_profile: single|str|None
    default_fade_ms: single|ms|None
    default_on_color: single|color|ffffff
    channels: single|dict|None
    x: single|float|None
    y: single|float|None
    z: single|float|None
light_channels:
    number: single|str|
    subtype: single|str|None
    platform: single|str|None
    platform_settings: single|dict|None
light_player:
    __valid_in__: machine, mode, show
    color: single|str|white
    fade: single|ms|None
    __allow_others__:
lisy:
    __valid_in__: machine
    port: single|str|None
    baud: single|int|None
    poll_hz: single|int|1000
    console_log: single|enum(none,basic,full)|none
    display_flash_frequency: single|float|1.0
    file_log: single|enum(none,basic,full)|basic
    connection: single|enum(network,serial)|network
    network_port: single|int|None
    network_host: single|str|None
logic_blocks_common:
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    restart_events: dict|str:ms|None
    reset_on_complete: single|bool|True
    disable_on_complete: single|bool|True
    persist_state: single|bool|False
    start_enabled: single|bool|None
    events_when_complete: list|str|None
    events_when_hit: list|str|None
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
accruals:
    __valid_in__: machine, mode
    events: list|str|
counters:
    __valid_in__: machine, mode
    count_events: dict|str:ms|
    count_complete_value: single|template_int|None
    multiple_hit_window: single|ms|0
    count_interval: single|int|1
    direction: single|str|up
    starting_count: single|template_int|0
sequences:
    __valid_in__: machine, mode
    events: list|str|
logging:
    __valid_in__: machine
    __allow_others__: true
machine:
    __valid_in__: machine
    balls_installed: single|int|1
    min_balls: single|int|1
machine_vars:
    __valid_in__: machine
    initial_value: single|str|
    value_type: single|enum(str,float,int)|int
    persist: single|bool|True
mc_scriptlets:
    __valid_in__: machine  # used by the MC, ignored by MPF
mma8451_accelerometer:
    i2c_platform: single|str|None
    i2c_address: single|str|29
mode:
    __valid_in__: mode
    priority: single|int|100
    start_events: list|str|None
    stop_events: list|str|None
    events_when_stopped: list|str|None
    events_when_started: list|str|None
    start_priority: single|int|0
    stop_priority: single|int|0
    game_mode: single|bool|True
    use_wait_queue: single|bool|False
    code: single|str|None
    stop_on_ball_end: single|bool|True
    restart_on_next_ball: single|bool|False
    console_log: single|enum(none,basic,full)|basic
    file_log: single|enum(none,basic,full)|basic
mode_settings:
    __valid_in__: mode
    __allow_others__:
modes:
    __valid_in__: machine                           # todo add to validator
magnets:
    __valid_in__: machine
    magnet_coil: single|machine(coils)|
    grab_switch: single|machine(switches)|None
    grab_time: single|ms|1.5s
    release_time: single|ms|500ms
    fling_drop_time: single|ms|250ms
    fling_regrab_time: single|ms|50ms
    playfield: single|machine(playfields)|playfield
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
    grab_ball_events: dict|str:ms|None
    release_ball_events: dict|str:ms|None
    fling_ball_events: dict|str:ms|None
motors:
    __valid_in__: machine
    position_switches: omap|str:machine(switches)|
    reset_position: single|str|
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
    go_to_position: dict|str:str|None
    motor_left_output: single|machine(digital_outputs)|None
    motor_right_output: single|machine(digital_outputs)|None
    include_in_ball_search: single|bool|True
mpf:
    __valid_in__: machine                           # todo add to validator
    default_pulse_ms: single|int|10
    default_flash_ms: single|int|50
    default_ball_search: single|bool|False
    default_light_hw_update_hz: single|int|50
    auto_create_switch_events: single|bool|True
    switch_event_active: single|str|%_active
    switch_event_inactive: single|str|%_inactive
    switch_tag_event: single|str|sw_%
    allow_invalid_config_sections: single|bool|false
    save_machine_vars_to_disk: single|bool|true
    default_show_sync_ms: single|int|0
    default_platform_hz: single|float|1000
    core_modules: ignore
    config_players: ignore
    device_modules: ignore
    plugins: ignore
    platforms: ignore
    paths: ignore
mpf-mc:
    __valid_in__: machine                           # todo add to validator
multiballs:
    __valid_in__: machine, mode
    ball_count: single|template_int|
    ball_count_type: single|enum(add,total)|total
    replace_balls_in_play: single|bool|false
    source_playfield: single|machine(ball_devices)|playfield
    shoot_again: single|ms|10s
    ball_locks: list|machine(ball_devices)|None
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting
    start_events: dict|str:ms|None
    stop_events: dict|str:ms|None
    add_a_ball_events: dict|str:ms|None
    start_or_add_a_ball_events: dict|str:ms|None
multiball_locks:
    __valid_in__: mode
    balls_to_lock: single|int|
    balls_to_replace: single|int|-1
    lock_devices: list|machine(ball_devices)|
    source_playfield: single|machine(ball_devices)|playfield
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    locked_ball_counting_strategy: single|enum(virtual_only,min_virtual_physical,physical_only,no_virtual)|virtual_only
    reset_all_counts_events: dict|str:ms|None
    reset_count_for_current_player_events: dict|str:ms|None
mypinballs:
    __valid_in__: machine
    port: single|str|
    baud: single|int|115200
    debug: single|bool|False
named_colors:
    __valid_in__: machine
opp:
    __valid_in__: machine
    ports: list|str|
    baud: single|int|115200
    debug: single|bool|False
    chains: dict|str:str|None
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
    poll_hz: single|int|100
open_pixel_control:
    __valid_in__: machine
    connection_required: single|bool|False
    host: single|str|localhost
    port: single|int|7890
    connection_attempts: single|int|-1
    debug: single|bool|False
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
p_roc:
    __valid_in__: machine
    lamp_matrix_strobe_time: single|ms|100ms
    watchdog_time: single|ms|1s
    use_watchdog: single|bool|True
    dmd_timing_cycles: list|int|None
    dmd_update_interval: single|ms|33ms
    debug: single|bool|False
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
p3_roc:
    __valid_in__: machine
    lamp_matrix_strobe_time: single|ms|100ms
    watchdog_time: single|ms|1s
    use_watchdog: single|bool|True
    debug: single|bool|False
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
p3_roc_accelerometer:
    number: single|int|1
psus:
    __valid_in__: machine
    voltage: single|int|None
    max_amps: single|int|None
    release_wait_ms: single|ms|10
player_vars:
    __valid_in__: machine
    initial_value: single|str|
    value_type: single|enum(str,float,int)|int
playfields:
    __valid_in__: machine
    enable_ball_search: single|bool|None
    ball_search_timeout: single|ms|15s
    ball_search_interval: single|ms|150ms
    ball_search_phase_1_searches: single|int|3
    ball_search_phase_2_searches: single|int|3
    ball_search_phase_3_searches: single|int|4
    ball_search_failed_action: single|str|new_ball
    ball_search_wait_after_iteration: single|ms|5s
    ball_search_block_events: dict|str:ms|flipper_cradle
    ball_search_unblock_events: dict|str:ms|flipper_cradle_release
    ball_search_enable_events: dict|str:ms|None
    ball_search_disable_events: dict|str:ms|None
    default_source_device: single|machine(ball_devices)|
playfield_transfers:
    __valid_in__: machine
    ball_switch: single|machine(switches)|None
    transfer_events: dict|str:ms|None
    eject_target: single|machine(ball_devices)|
    captures_from: single|machine(ball_devices)|
playlist_player:
    __valid_in__: machine, mode, show
    __allow_others__:
    action: single|enum(play,stop,advance,set_repeat)|play
playlist_player_actions:
    play:
        action: ignore
        playlist: single|str|
        volume: single|gain|None
        crossfade_mode: single|enum(use_track_setting,override,use_playlist_setting)|use_playlist_setting
        crossfade_time: single|secs|None
        shuffle: single|bool|None
        repeat: single|bool|None
        scope: single|enum(machine,player,use_playlist_setting)|use_playlist_setting
        events_when_played: list|str|use_playlist_setting
        events_when_stopped: list|str|use_playlist_setting
        events_when_looping: list|str|use_playlist_setting
        events_when_sound_changed: list|str|use_playlist_setting
        events_when_sound_stopped: list|str|use_playlist_setting
    stop:
        action: ignore
        fade_out: single|secs|0
    advance:
        action: ignore
        none: ignore
    set_repeat:
        action: ignore
        repeat: single|bool|True
playlists:
    __valid_in__: machine, mode
    crossfade_mode: single|enum(use_track_setting,override)|use_track_setting
    crossfade_time: single|secs|0
    shuffle: single|bool|False
    repeat: single|bool|False
    scope: single|enum(machine,player)|machine
    sounds: list|str|
    events_when_played: list|str|None
    events_when_stopped: list|str|None
    events_when_looping: list|str|None
    events_when_sound_changed: list|str|None
    events_when_sound_stopped: list|str|None
plugins:
    __valid_in__: machine                      # todo add to validator
pololu_maestro:
    __valid_in__: machine
    port: single|str|
    servo_min: single|int|3000
    servo_max: single|int|9000
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
    debug: single|bool|False
random_event_player:
    __valid_in__: machine, mode, show
    events: ignore
    force_different: single|bool|true
    force_all: single|bool|true
    disable_random: single|bool|false
    scope: single|enum(player,machine)|player
raspberry_pi:
    __valid_in__: machine
    ip: single|str|
    port: single|int|8888
rgb_dmds:
    __valid_in__: machine
    platform: single|str|None
    fps: single|int|30
    source_display: single|str|dmd
    only_send_changes: single|bool|False
    brightness: single|float|1.0
    gamma: single|float|2.2
    hardware_brightness: single|template_float|1.0
score_reels:
    __valid_in__: machine
    coil_inc: single|machine(coils)|None
    rollover: single|bool|True
    limit_lo: single|int|0
    limit_hi: single|int|9
    repeat_pulse_time: single|ms|200
    hw_confirm_time: single|ms|20
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
score_reel_groups:
    __valid_in__: machine
    max_simultaneous_coils: single|int|2
    reels: list|machine(score_reels)|
    chimes: list|machine(coils)|None
    lights_tag: single|str|None
scriptlets:
    __valid_in__: machine                           # todo add to validator
segment_displays:
    __valid_in__: machine
    number: single|str|
    platform: single|str|None
segment_display_player:
    __valid_in__: machine, mode, show
    priority: single|int|0
    text: single|str|None
    action: single|enum(add,remove,flash,no_flash)|add
    key: single|str|None
    expire: single|ms|None
servo_controllers:
    __valid_in__: machine
    platform: single|str|None
    address: single|str|64
    servo_min: single|int|150
    servo_max: single|int|600
    debug: single|bool|False
servos:
    __valid_in__: machine
    positions: dict|float:str|None
    servo_min: single|float|0.0
    servo_max: single|float|1.0
    ball_search_min: single|float|0.0
    ball_search_max: single|float|1.0
    speed_limit: single|float|-1.0
    acceleration_limit: single|float|-1.0
    ball_search_wait: single|ms|5s
    include_in_ball_search: single|bool|True
    reset_position: single|float|0.5
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting, ball_will_end, service_mode_entered
    number: single|str|
    platform: single|str|None
settings:
    __valid_in__: machine
    label: single|str|
    sort: single|int|
    values: dict|str:str|
    key_type: single|enum(str,float,int)|str
    default: single|str|
    machine_var: single|str|None
shots:
    __valid_in__: mode
    profile: single|machine(shot_profiles)|default
    switch: list|machine(switches)|None
    switches: list|machine(switches)|None
    start_enabled: single|bool|None
    delay_switch: dict|machine(switches):ms|None
    persist_enable: single|bool|True
    playfield: single|machine(playfields)|playfield
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    advance_events: dict|str:ms|None
    hit_events: dict|str:ms|None
    show_tokens: dict|str:str|None
shot_groups:
    __valid_in__: mode
    shots: list|machine(shots)|None
    rotate_events: dict|str:ms|None
    rotate_left_events: dict|str:ms|None
    rotate_right_events: dict|str:ms|None
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    enable_rotation_events: dict|str:ms|None
    disable_rotation_events: dict|str:ms|None
shot_profiles:
    __valid_in__: machine, mode
    loop: single|bool|False
    show: single|str|None
    advance_on_hit: single|bool|True
    state_names_to_rotate: list|str|None
    state_names_to_not_rotate: list|str|None
    rotation_pattern: list|str|R
    show_when_disabled: single|bool|False
    block: single|bool|False
    states:
        show: single|str|None
        name: single|str|
        priority: single|int|0
        speed: single|float|1
        start_step: single|int|None
        loops: single|int|-1
        sync_ms: single|int|None
        manual_advance: single|bool|None
        show_tokens: dict|str:str|None
state_machines:
    __valid_in__: machine, mode
    states: dict|str:subconfig(state_machine_states)|
    transitions: list|subconfig(state_machine_transitions)|
    persist_state: single|bool|False
state_machine_transitions:
    source: list|str|
    target: single|str|
    events: list|str|
    events_when_transitioning: list|str|None
state_machine_states:
    label: single|str|None
    show_when_active: single|subconfig(show_config)|None
    events_when_started: list|str|None
    events_when_stopped: list|str|None
show_config:
    show: single|str|
    show_tokens: dict|str:str|None
    manual_advance: single|bool|None
    sync_ms: single|int|None
    loops: single|int|-1
    priority: single|int|0
    speed: single|float|1
    start_step: single|int|1
show_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,stop,pause,resume,advance,step_back,update)|play
    show: single|str|None
    priority: single|int|0
    speed: single|float|1
    block_queue: single|bool|False
    start_step: single|template_int|1
    loops: single|int|-1
    sync_ms: single|int|None
    manual_advance: single|bool|False
    key: single|str|None
    show_tokens: dict|str:str|None
    events_when_played: list|str|None
    events_when_stopped: list|str|None
    events_when_looped: list|str|None
    events_when_paused: list|str|None
    events_when_resumed: list|str|None
    events_when_advanced: list|str|None
    events_when_stepped_back: list|str|None
    events_when_updated: list|str|None
    events_when_completed: list|str|None
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
    background_color: single|kivycolor|000000ff
    priority: single|int|None                      # todo should this be 0?
    show: single|bool|True
    force: single|bool|False
    transition: ignore
    transition_out: ignore
    widgets: ignore
    expire: single|secs|None
    slide: single|str|None
    action: single|enum(play,remove)|play
slides:
    __valid_in__: machine, mode
    debug: single|bool|False
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
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
smartmatrix:
    __valid_in__: machine
    port: single|str|
    baud: single|int|
    old_cookie: single|bool|False
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
smart_virtual:
    __valid_in__: machine
    simulate_manual_plunger: single|bool|False
    simulate_manual_plunger_timeout: single|ms|10s
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
sound_loop_player:
    __valid_in__: machine, mode, show
    __allow_others__:
    action: single|enum(play,stop,stop_looping,jump_to,play_layer,stop_layer,stop_looping_layer)|play
sound_loop_player_actions:
    play:
        action: ignore
        sound_loop_set: single|str|
        volume: single|gain|None
        fade_in: single|secs|None
        fade_out: single|secs|None
        start_at: single|secs|0
        timing: single|enum(now,loop_end,next_beat_interval,next_time_interval)|loop_end
        interval: single|float|1
        synchronize: single|bool|False
        events_when_played: list|str|use_sound_loop_setting
        events_when_stopped: list|str|use_sound_loop_setting
        events_when_looping: list|str|use_sound_loop_setting
        mode_end_action: single|enum(stop,stop_looping,use_sound_loop_setting)|use_sound_loop_setting
    stop:
        action: ignore
        fade_out: single|secs|None
    stop_looping:
        action: ignore
        none: ignore
    jump_to:
        action: ignore
        time: single|secs|0
    play_layer:
        action: ignore
        layer: single|int|
        volume: single|gain|None
        timing: single|enum(now,loop_end)|loop_end
        fade_in: single|secs|0
    stop_layer:
        action: ignore
        layer: single|int|
        fade_out: single|secs|0
    stop_looping_layer:
        action: ignore
        layer: single|int|
sound_loop_sets:
    __valid_in__: machine, mode
    sound: single|str|
    volume: single|gain|None
    tempo: single|float|60.0
    layers:
        sound: single|str|
        volume: single|gain|None
        initial_state: single|enum(play,stop)|play
    events_when_played: list|str|None
    events_when_stopped: list|str|None
    events_when_looping: list|str|None
    fade_in: single|secs|0
    fade_out: single|secs|0
    mode_end_action: single|enum(stop,stop_looping)|stop
sound_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,stop,stop_looping,load,unload)|play
    track: single|str|use_sound_setting
    volume: single|gain|None
    pan: single|float|0
    loops: single|int|None
    priority: single|int|None
    start_at: single|secs|None
    fade_in: single|secs|None
    fade_out: single|secs|None
    about_to_finish_time: single|secs|-1
    max_queue_time: single|secs|-1
    events_when_played: list|str|use_sound_setting
    events_when_stopped: list|str|use_sound_setting
    events_when_looping: list|str|use_sound_setting
    events_when_about_to_finish: list|str|use_sound_setting
    mode_end_action: single|enum(stop,stop_looping,use_sound_setting)|use_sound_setting
    key: single|str|None
sound_pools:
    __valid_in__: machine, mode                      # todo add to validator
sound_system:
    __valid_in__: machine
    enabled: single|bool|True
    buffer: single|int|2048
    frequency: single|int|44100
    channels: single|int|1
    master_volume: single|gain|0.5
    tracks:
        common:
            type: single|enum(standard,sound_loop,playlist)|standard
            volume: single|gain|0.5
            events_when_played: list|str|None
            events6_when_stopped: list|str|None
            events_when_paused: list|str|None
            events_when_resumed: list|str|None
            ducking:
                target: list|str|
                delay: single|secs|0
                attack: single|secs|10ms
                attenuation: single|gain|1.0
                release_point: single|secs|0
                release: single|secs|10ms
        standard:
            simultaneous_sounds: single|int|8
        sound_loop:
            max_layers: single|int|8
        playlist:
            crossfade_time: single|secs|0
sounds:
    __valid_in__: machine, mode
    file: single|str|None
    track: single|str|None
    volume: single|gain|0.5
    streaming: single|bool|False
    loops: single|int|0
    priority: single|int|0
    start_at: single|secs|0
    fade_in: single|secs|0
    fade_out: single|secs|0
    about_to_finish_time: single|secs|None
    max_queue_time: single|secs|None
    simultaneous_limit: single|int|None
    stealing_method: single|enum(skip,oldest,newest)|oldest
    events_when_played: list|str|None
    events_when_stopped: list|str|None
    events_when_looping: list|str|None
    events_when_about_to_finish: list|str|None
    mode_end_action: single|enum(stop,stop_looping)|stop_looping
    key: single|str|None
    markers: ignore                                 # todo add subconfig
    ducking:
        target: list|str|
        delay: single|secs|0
        attack: single|secs|10ms
        attenuation: single|gain|1.0
        release_point: single|secs|0
        release: single|secs|10ms
spike:
    __valid_in__: machine
    debug: single|bool|False
    port: single|str|
    baud: single|int|
    runtime_baud: single|int|921600
    flow_control: single|bool|False
    nodes: list|int|
    poll_hz: single|int|1000
    use_send_key: single|bool|False
    connection: single|enum(shell)|shell
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
    wait_times: dict|int:int|None
steppers:
    __valid_in__: machine
    mode: single|enum(position,velocity)|position
    named_positions: dict|float:str|None
    pos_min: single|float|0.0
    pos_max: single|float|1.0
    move_current: single|int|20
    hold_current: single|int|0
    microstep_per_fullstep: single|int|16
    velocity_limit: single|float|1.0
    acceleration_limit: single|float|1.0
    homing_direction: single|enum(clockwise,counterclockwise)|clockwise
    homing_speed: single|float|1.0
    fullstep_per_userunit: single|float|1.0
    ball_search_min: single|float|0.0
    ball_search_max: single|float|1.0
    ball_search_wait: single|ms|5s
    include_in_ball_search: single|bool|True
    reset_position: single|float|0.0
    reset_events: dict|str:ms|machine_reset_phase_3, ball_starting, ball_will_end, service_mode_entered
    number: single|str|
    platform: single|str|None
switch_player:
    __valid_in__: machine
    start_event: single|str|machine_reset_phase_3
    steps: ignore
sequence_shots:
    __valid_in__: machine, mode
    switch_sequence: list|machine(switches)|None
    event_sequence: list|str|None
    cancel_switches: list|machine(switches)|None
    cancel_events: dict|str:ms|None
    delay_switch_list: dict|machine(switches):ms|None
    delay_event_list: dict|str:ms|None
    sequence_timeout: single|ms|0
    playfield: single|machine(playfields)|playfield
switches:
    __valid_in__: machine
    number: single|str|
    type: single|enum(NC,NO)|NO
    debounce: single|enum(auto,quick,normal)|auto
    ignore_window_ms: single|ms|0
    events_when_activated: list|str|None
    events_when_deactivated: list|str|None
    platform: single|str|None
    platform_settings: single|dict|None
    x: single|float|None
    y: single|float|None
    z: single|float|None
fast_switches:
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
    warnings_to_tilt: single|template_int|3
    reset_warnings_events: list|str|ball_will_end
    multiple_hit_window: single|ms|300ms
    settle_time: single|ms|5s
    tilt_warnings_player_var: single|str|tilt_warnings
timed_switches:
    __valid_in__: machine, mode
    switches: list|machine(switches)|None
    switch_tags: list|str|None
    time: single|ms|
    state: single|enum(active,inactive)|active
    events_when_active: list|str|None
    events_when_released: list|str|None
timers:
    __valid_in__: mode
    debug: single|bool|False
    start_value: single|template_int|0
    end_value: single|template_int|None
    direction: single|str|up
    max_value: single|int|None
    tick_interval: single|template_secs|1s
    start_running: single|bool|False
    control_events: list|subconfig(timer_control_events)|None
    restart_on_complete: single|bool|False
    bcp: single|bool|False
    console_log: single|enum(none,basic,full)|none
    file_log: single|enum(none,basic,full)|basic
timer_control_events:  # subconfig for mode timers
    __valid_in__: None
    action: single|enum(add,subtract,jump,start,stop,reset,restart,pause,set_tick_interval,change_tick_interval,\
reset_tick_interval)|
    event: single|str|
    value: single|int|None
track_player:
    __valid_in__: machine, mode, show
    action: single|enum(play,stop,pause,set_volume,stop_all_sounds)|
    volume: single|gain|None
    fade: single|secs|0.1sec
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
    card:
        type: single|str|
        mode: single|enum(push,pop)|push
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
trinamics_steprocker:
    __valid_in__: machine
    port: single|str|
variable_player:
    __valid_in__: modes
    int: single|template_int|0
    float: single|template_float|None
    string: single|str|None
    block: single|bool|False
    action: single|enum(add,set,add_machine,set_machine)|add
    player: single|int|None
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
    slide: single|str|None
    action: single|enum(add,remove,update)|add
    key: single|str|None
    widget_settings: ignore
    target: single|str|None
widget_styles:
    __valid_in__: machine, mode, show
    color: single|kivycolor|ffffffff
    __allow_others__:
widgets:
    __valid_in__: machine, mode
    common:
        type: single|str|
        x: single|str|None
        y: single|str|None
        anchor_x: single|str|center
        anchor_y: single|str|center
        round_anchor_x: single|str|None
        round_anchor_y: single|str|None
        opacity: single|float|1.0
        z: single|int|0
        animations: ignore
        reset_animations_events: list|str|None
        color: single|kivycolor|ffffffff
        style: single|str|None
        adjust_top: single|int|0
        adjust_bottom: single|int|0
        adjust_left: single|int|0
        adjust_right: single|int|0
        expire: single|secs|None
        key: single|str|None
    animations:
        property: list|str|
        value: list|str|
        relative: single|bool|False
        duration: single|secs|1
        timing: single|enum(after_previous,with_previous)|after_previous
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
        rotation: single|float|0
        scale: single|float|1.0
    camera:
        width: single|num|
        height: single|num|
        camera_index: single|int|-1
    display:
        width: single|num|
        height: single|num|
        source_display: single|str|dmd
        effects: ignore
    ellipse:
        width: single|num|
        height: single|num|
        segments: single|int|180
        angle_start: single|int|0
        angle_end: single|int|360
        rotation: single|float|0
        scale: single|float|1.0
    image:
        allow_stretch: single|bool|False
        fps: single|int|10
        loops: single|int|-1
        keep_ratio: single|bool|False
        image: single|str|
        height: single|int|0
        width: single|int|0
        auto_play: single|bool|True
        start_frame: single|int|0                          # todo
        rotation: single|int|0
        scale: single|float|1.0
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
        pointsize: single|float|1.0
        rotation: single|int|0
        scale: single|float|1.0
    quad:
        points: list|num|
        rotation: single|int|0
        scale: single|float|1.0
    rectangle:
        width: single|float|
        height: single|float|
        corner_radius: single|int|0
        corner_segments: single|int|10
        rotation: single|int|0
        scale: single|float|1.0
    text:
        text: single|str|
        font_size: single|num|15
        font_name: ignore
        bitmap_font: single|bool|False
        font_kerning: single|bool|True
        bold: single|bool|False
        italic: single|bool|False
        number_grouping: single|bool|False
        min_digits: single|int|0
        halign: single|str|center
        valign: single|str|middle
        rotation: single|int|0
        scale: single|float|1.0
        casing: single|str|None
        # outline_color: single|kivycolor|ffffffff
        # outline_width: single|int|0
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
        number_grouping: single|bool|False
        min_digits: single|int|0
        max_chars: single|int|3
        char_list: "single|str|ABCDEFGHIJKLMNOPQRSTUVWXYZ_- "
        keep_selected_char: single|bool|True
        dynamic_x: single|bool|True
        dynamic_x_pad: single|int|0
    triangle:
        points: list|num|
        rotation: single|int|0
        scale: single|float|1.0
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
    effects: ignore
'''.format(__version__)
