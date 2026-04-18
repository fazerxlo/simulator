"""
Virtual car state for the Peugeot 407 CAN 2004 simulator.

Each car subsystem has a dedicated state object. Modules update these
objects; CAN frame encoders read from them to produce bus traffic.

This design ensures each CAN ID has exactly one source of truth even
when multiple UI modules are loaded simultaneously, eliminating the
message-conflict problem described in the project structure issue.
"""


class BSI:
    """Body Systems Interface and drivetrain state."""

    def __init__(self):
        self.ignition_on = False
        self.power_mode = 0x02
        self.economy = 0
        self.dash_lights = 0
        self.dark_mode = 0
        self.lum = 15
        self.startup_banner_pending = False
        self.engine_running = 0
        # 0 = off, 1 = side, 2 = low beam, 3 = high beam
        self.light_mode = 0
        self.rpm = 0
        self.speed = 0
        self.fuel = 0
        self.oil = 0
        # Oil level in percent (0-100). 0xFF = invalid/not available.
        self.oil_level = 0xFF
        self.coolant = 0
        self.temperature = 20
        self.reverse = 0
        # Blinker state from 0x0F6 byte 7 bits 1-0 (PSA-RE BLINKERS_STATUS).
        # 0 = none, 1 = right, 2 = left, 3 = both (hazards).
        self.blinkers = 0


class Clim:
    """Climate control state."""

    def __init__(self):
        self.fan = 0
        self.dir_left = 0
        self.dir_right = 0
        self.temp_left = 0
        self.temp_right = 0
        self.unfrost_front = 0
        self.unfrost_rear = 0
        self.recycle = 0
        self.auto = 0
        self.dual = 0
        self.bits = 0
        # Set to True by the clim module so that Msg1D0/Msg1E3 switch from the
        # BSI idle encoding to the full climate encoding.
        self.enabled = False


class Doors:
    """Door and panel opening state."""

    def __init__(self):
        self.front_left = 0
        self.front_right = 0
        self.rear_left = 0
        self.rear_right = 0
        self.boot = 0
        self.bonnet = 0
        self.rear_window = 0
        self.fuel_flap = 0
        # True while a door-open popup is being displayed on the MFD
        self.display_active = False
        # Last popup message ID used on 0x1A1 so the clear frame can match it.
        self.popup_msg_id = 0x0B


class Parktronic:
    """Parking sensor distances and activation state."""

    def __init__(self):
        self.display = 0
        self.front_active = 0
        self.rear_active = 0
        # Sensor values: 7 = inactive / no object, 0 = closest
        self.rear_left = 7
        self.rear_center = 7
        self.rear_right = 7
        self.front_left = 7
        self.front_center = 7
        self.front_right = 7


class Tyres:
    """Tyre pressure monitoring state."""

    # Tyre condition constants
    OK = 0
    LOW = 1
    FLAT = 2
    NO_DATA = 3

    def __init__(self):
        self.fl = Tyres.OK
        self.fr = Tyres.OK
        self.rl = Tyres.OK
        self.rr = Tyres.OK
        # True while a tyre-warning popup is being displayed on the MFD
        self.display_active = False
        # Byte 1 value for the 0x168 dashboard alert frame
        self.alert_0x168_b1 = 0


class Dashboard:
    """Combined dashboard indicator state (drives 0x128 and 0x168).

    The ``active`` flag is set by the combine module when it loads.
    When active, the combine module owns the 0x128 and 0x168 senders;
    bsi-base will skip registering 0x128 in that case.
    """

    def __init__(self):
        # 0x128 — cluster warning and lamp status
        self.airbag_pass = 0
        self.seatbelt = 0
        self.brakes = 0
        self.low_fuel = 0
        self.preheat = 0
        self.warn = 0
        self.stop = 0
        self.doors = 0
        self.esp = 0
        self.esp_blink = 0
        self.tyre = 0
        self.backlight = 0
        self.on = 0
        self.low_beam = 0
        self.high_beam = 0
        self.fog_front = 0
        self.fog_rear = 0
        self.clig_r = 0
        self.clig_l = 0
        # 0x168 — warning and signal lamps
        self.coolant_warn = 0
        self.oil_blink = 0
        self.coolant_blink = 0
        self.oil_warn = 0
        self.abs = 0
        self.obd = 0
        self.gas_water = 0
        self.airbag = 0
        self.battery = 0
        self.dae = 0
        self.eco_blink = 0
        self.eco = 0
        self.battery_blink = 0
        self.obd_blink = 0
        # True when the combine module is loaded and owns 0x128 / 0x168
        self.active = False


class Radio:
    """Radio / head-unit state."""

    # Maps input source names to the 0x165 byte-2 nibble codes.
    INPUT_CODES = {
        'TUN': 0x01, 'CD': 0x02, 'CDC': 0x03,
        'AUX1': 0x04, 'AUX2': 0x05, 'USB': 0x06, 'BT': 0x07,
    }

    def __init__(self):
        self.input = 'TUN'
        self.volume = 15
        # 0xE0 = stable; 0x00 = volume-change in progress
        self.volflag = 0xE0
        self.panel = {k: 0 for k in (
            'mode', 'menu', 'ok', 'esc', 'up', 'down',
            'right', 'left', 'audio', 'trip', 'clim', 'tel',
        )}
        self.audio = {
            'bass': 0x3F, 'treble': 0x3F,
            'rf-bal': 0x3F, 'lr-bal': 0x3F,
            'loudness': 0, 'volume': 0, 'ambiance': 'none', 'menu': 'none',
        }


class Trip:
    """Trip computer state."""

    def __init__(self):
        self.hide_fuel = 0
        self.hide_dist = 0
        self.com_left = 0
        self.com_right = 0
        self.fuel = 7.1
        self.autonomy = 740
        self.dist = 120
        # Two historical trip records, each with speed / dist / fuel fields.
        self.hist = [
            {'speed': 37, 'dist': 569, 'fuel': 7.3},
            {'speed': 35, 'dist': 921, 'fuel': 7.9},
        ]


class KMLState:
    """Hands-free / KML module state."""

    def __init__(self):
        self.opt = 0
        # Dynamic bits driven by the KML module UI toggles.
        self.bits_223 = 0
        # bits_323 is decoded from received 0x323 frames (read-only from bus).
        self.bits_323 = 0


class BTEState:
    """BTE module state."""

    def __init__(self):
        self.bits = 0


class Buttons:
    """Steering wheel and physical button state.

    The ``active`` flag is set by the ``buttons`` module when it loads.
    When active, ``Msg1A5`` and ``Msg3E5`` encode from this object instead
    of ``car.radio``, allowing the lightweight buttons module to run
    independently of the full ``radio-gen`` head-unit module.

    Pulse-tick tracking keeps button press assertions alive for a few
    CAN frames (``_pulse_window`` encodes), matching the physical behaviour
    of momentary steering-wheel buttons.
    """

    BUTTON_KEYS = (
        'source', 'trip', 'clima', 'tel', 'dark',
        'ok', 'esc', 'up', 'down', 'next', 'prev', 'right', 'left',
    )

    def __init__(self):
        self.active = False
        self.volume = 15
        # 0xE0 = stable; 0x00 = volume-change in progress
        self.volflag = 0xE0
        self._volume_action_ticks = 0
        self.panel = {k: 0 for k in self.BUTTON_KEYS}
        self._pulse_ticks = {k: 0 for k in self.BUTTON_KEYS}
        self._pulse_window = 3

    def press(self, key: str) -> None:
        """Assert a button for one pulse window.

        The button stays asserted for ``_pulse_window`` encode ticks; since
        ``Msg3E5.period_ms`` is 50 ms the default window of 3 ticks is ~150 ms,
        but the actual duration scales with the message period.
        """
        if key not in self.panel:
            return
        self.panel[key] = 1
        self._pulse_ticks[key] = self._pulse_window

    def step_pulses(self) -> bool:
        """Advance button pulse timers by one tick. Returns True if any changed."""
        changed = False
        for key in self.BUTTON_KEYS:
            if self._pulse_ticks.get(key, 0) > 0:
                self._pulse_ticks[key] -= 1
                if self._pulse_ticks[key] == 0 and self.panel[key] != 0:
                    self.panel[key] = 0
                    changed = True
        return changed

    def step_volume(self) -> None:
        """Advance the volume volflag timer by one tick.

        Called from ``Msg1A5.encode()`` at each transmit cycle.  Once
        ``_volume_action_ticks`` reaches zero the volflag is reset to 0xE0
        (stable / no-change), stopping the "volume in progress" indication
        sent to the head unit.
        """
        if self._volume_action_ticks > 0:
            self._volume_action_ticks -= 1
            if self._volume_action_ticks == 0:
                self.volflag = 0xE0

    def volume_up(self) -> None:
        """Increase volume by one step and signal a volume change."""
        self.volume = min(30, self.volume + 1)
        self.volflag = 0x00
        self._volume_action_ticks = 3

    def volume_down(self) -> None:
        """Decrease volume by one step and signal a volume change."""
        self.volume = max(0, self.volume - 1)
        self.volflag = 0x00
        self._volume_action_ticks = 3


class MFDPopup:
    """State for the BSI-log MFD popup messages (0x1A1 arbitration).

    The bsi-log module drives ``flag`` / ``msg_id`` through its state
    machine; the Msg1A1 message object reads from here to produce periodic
    transmissions.  When ``flag`` is 0xFF no popup is pending.
    """

    def __init__(self):
        self.flag = 0xFF   # 0xFF = inactive / no message pending
        self.msg_id = 0x00


class SpeedControl:
    """Speed regulator / limiter state (drives 0x1A8).

    Mirrors the PSA-RE ``SPEED_CONTROL`` / ``GESTION_VITESSE`` frame.
    """

    # SPEED_CONTROL_TYPE values (bits 7-6 of byte 0)
    NONE = 0
    REGULATOR = 1
    LIMITER = 2
    ADAPTIVE = 3

    # ACTIVE_FUNCTION_STATUS values (bits 5-3 of byte 0)
    STANDBY = 0
    ACTIVE = 1
    LIMITER_ACTIVE = 2
    OVERSPEED_NO_PEDAL = 3
    OVERSPEED_PEDAL = 4
    NOT_ACTIVATABLE = 6
    FAULT = 7

    def __init__(self):
        # Control type: NONE / REGULATOR / LIMITER / ADAPTIVE
        self.control_type = SpeedControl.NONE
        # Function status: STANDBY / ACTIVE / LIMITER_ACTIVE / FAULT / etc.
        self.function_status = SpeedControl.STANDBY
        # Whether a new activation was attempted this cycle
        self.activation_attempt = 0
        # Speed set-point in km/h. 0xFFFF (encoded) means not set.
        # Valid range 0–254 km/h; use None to encode invalid (0xFFFF).
        self.set_speed: float | None = None
        # Speed unit: False = km/h, True = mph
        self.unit_mph = False
        # Partial trip odometer in km. None encodes as 0xFFFFFF (invalid).
        self.partial_odo: float | None = None


class CDChanger:
    """CD changer emulator state.

    The CDC module transmits periodic status frames (0x1A0) and receives
    command frames (0x131) from the head unit.  This object holds the
    playback state that those frames encode and decode.
    """

    # Status constants (byte 0 of 0x1A0)
    STATUS_IDLE = 0
    STATUS_PLAYING = 1
    STATUS_PAUSED = 2
    STATUS_LOADING = 3
    STATUS_SEARCHING = 4

    def __init__(self):
        # Set to True by the cdc module when it loads.
        self.active = False

        # Playback state: one of STATUS_* constants above.
        self.status = CDChanger.STATUS_IDLE

        # Current disc (1-6).
        self.disc = 1
        # Current track number (1-99).
        self.track = 1
        # Track elapsed time.
        self.minutes = 0
        self.seconds = 0
        # Per-disc track counts (disc 1-6 → number of tracks).
        self.disc_tracks = {i: 10 for i in range(1, 7)}

        # Playback mode flags.
        self.random = False
        self.repeat = False        # repeat all tracks
        self.repeat_track = False  # repeat current track
        self.scan = False

    @property
    def total_tracks(self):
        """Total tracks on the current disc (reads from disc_tracks)."""
        return self.disc_tracks.get(self.disc, 10)

    @total_tracks.setter
    def total_tracks(self, value):
        """Set the total track count for the current disc."""
        self.disc_tracks[self.disc] = value


class VirtualCar:
    """Shared virtual car state for the Peugeot 407 simulator.

    Every simulation module receives a reference to this object and uses it
    to exchange state with other modules.  CAN frame senders encode bus
    traffic directly from this shared state, so each CAN ID has exactly
    one source of truth even when multiple UI modules are loaded at the
    same time.

    Usage::

        car = VirtualCar()
        runner = CanRunner(car=car)
        # modules receive runner and access car via runner.car
        bsi_module = BSI_base(runner)
        # bsi_module reads/writes runner.car.bsi.*
    """

    def __init__(self):
        self.bsi = BSI()
        self.clim = Clim()
        self.doors = Doors()
        self.parktronic = Parktronic()
        self.tyres = Tyres()
        self.dashboard = Dashboard()
        self.radio = Radio()
        self.trip = Trip()
        self.kml = KMLState()
        self.bte = BTEState()
        self.buttons = Buttons()
        self.mfd_popup = MFDPopup()
        self.speed_control = SpeedControl()
        self.cdc = CDChanger()
