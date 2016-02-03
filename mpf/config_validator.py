# values are type|validation|default

config_spec = '''

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
    jam_switch: single|self.machine.switches[%]|None
    confirm_eject_type: single|str|target
    captures_from: single|str|playfield
    eject_targets: list|str|playfield
    # can't convert eject_targets to objects til all ball_devices are setup
    eject_timeouts: list|ms|None
    ball_missing_timeouts: list|ms|None
    ball_missing_target: single|str|playfield
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
color_correction_profile:
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
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
    bits_per_pixel: single|int|24
    default: single|bool|False
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
fadecandy:
    gamma: single|float|2.5
    whitepoint: list|float|1.0, 1.0, 1.0
    linear_slope: single|float|1.0
    linear_cutoff: single|float|0.0
    keyframe_interpolation: single|bool|True
    dithering: single|bool|True
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
led_settings:
    color_correction_profiles: single|dict|None
    default_color_correction_profile: single|str|None
    default_led_fade_ms: single|int|0
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
playfields:
    eject_targets: list|str|None
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
    switch: list|self.machine.switches[%]|None
    switch_sequence: list|self.machine.switches[%]|None
    cancel_switch: list|self.machine.switches[%]|None
    delay_switch: dict|self.machine.switches[%]:ms|None
    time: single|ms|0
    light: list|self.machine.lights[%]|None
    led: list|self.machine.leds[%]|None
    tags: list|str|None
    label: single|str|%
    debug: single|bool|False
    enable_events: dict|str:ms|None
    disable_events: dict|str:ms|None
    reset_events: dict|str:ms|None
    advance_events: dict|str:ms|None
    hit_events: dict|str:ms|None
    remove_active_profile_events: dict|str:ms|None
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
    state_names_to_rotate: list|str|None
    state_names_to_not_rotate: list|str|None
    rotation_pattern: list|str|R
    player_variable: single|str|None
    advance_on_hit: single|bool|True
    lights_when_disabled: single|bool|True
    block: single|bool|true
    states:
        name: single|str|
        light_script: single|str|None
        hold: single|bool|True
        reset: single|bool|False
        repeat: single|bool|True
        blend: single|bool|False
        tocks_per_sec: single|int|10
        num_repeats: single|int|0
        sync_ms:  single|int|0
slide_player:
    slide: single|str|
    target: single|str|None
    priority: single|int|None
    show: single|bool|True
    force: single|bool|False
    transition: ignore
snux:
    flipper_enable_driver_number: single|int|c23
    diag_led_driver_number: single|str|c24
switches:
    number: single|str|
    number_str: single|str|
    type: single|str|NO
    debounce: single|bool|True
    recycle_time: single|ticks|0
    activation_events: list|str|None
    deactivation_events: list|str|None
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
    color: single|color|ffffffff
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
timing:
    hz: single|int|30
    hw_thread_sleep_ms: single|int|1
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


widgets:
    animations:
        property: list|str|
        value: list|str|
        duration: single|secs|1
        timing: single|str|after_previous
        repeat: single|bool|False
        easing: single|str|linear
    common:
        type: single|str|slide_frame
        x: single|str|None
        y: single|str|None
        anchor_x: single|str|None
        anchor_y: single|str|None
        opacity: single|float|1.0
        z: single|int|0
        animations: ignore
        color: single|color|ffffffff
    bezier:
        points: list|num|
        thickness: single|float|1.0
        cap: single|str|round
        joint: single|str|round
        cap_precision: single|int|10
        joint_precision: single|int|10
        close: single|bool|False
        precision: single|int|180
    dmd:
        width: single|num|
        height: single|num|
        source_display: single|str|dmd
        luminosity: list|float|.299, .587, .114
        gain: single|float|1.0
        color: single|color|ff7700  # classic DMD orange
        shades: single|int|16
    ellipse:
        width: single|num|
        height: single|num|
        segments: single|int|180
        angle_start: single|int|0
        angle_end: single|int|360
    image:
        allow_stretch: single|bool|False
        anim_delay: single|float|.25
        anim_loop: single|int|0
        keep_ratio: single|bool|False
        image: single|str|
        height: single|int|0
        width: single|int|0
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
    widget: list|str|
    target: single|str|None
    slide: single|str|None

auditor:
    save_events: list|str|ball_ended
    audit: list|str|None
    events: list|str|None
    player: list|str|None
    num_player_top_records: single|int|1

fast:
    ports: list|str|
    baud: single|int|921600
    config_number_format: single|str|hex
    watchdog: single|ms|1000
    default_debounce_open: single|ms|30
    default_debounce_close: single|ms|30
    hardware_led_fade_time: single|ms|0
    debug: single|bool|False
'''
