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
        self.vin = 'VF3TEST1234567890'
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
        # Navigation matrix repeat (0x0A9)
        self.nav_active = False
        self.nav_recalc = False
        self.nav_picto = 0
        self.nav_altitude = 0
        self.nav_dist_dest = 0
        self.nav_dist_maneuver = 0
        self.nav_eta_hour = 0
        self.nav_eta_minute = 0
        # Wheel pulse counters (0x0E6)
        self.wheel_ticks_rr = 0x7FFF
        self.wheel_ticks_rl = 0x7FFF
        # Functions status (0x2E1)
        self.wipers_front = 0
        self.wipers_rear = 0
        # Crash status (0x269)
        self.crash_confirmed = 0
        # Maintenance (0x3A7)
        self.service_spanner = 0
        self.service_countdown = 15000


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
        # A/C compressor enable flag. Encoded in 0x1E3 byte 0 bit 4.
        # Default 1 (on) so that the existing workbench constant 0x14/0x1C is
        # produced without any extra module initialisation.
        self.ac = 1
        # True when an explicit intake mode (Fresh, Recirc, or UnfrostFront) was
        # activated by the user.  Clears on AUTO or full OFF reset.  Controls
        # bit5 of 0x1D0 byte4 and bit2 of 0x1E3 byte0 per workbench analysis.
        self.intake_explicit = False
        # One-shot notification flag.  Set to True by on_airflow_mode when the
        # user selects Recirc or Fresh; consumed (and cleared) by Msg1E3.encode
        # on the very next frame to set bit1 (0x02) of 0x1E3 byte0.
        # Workbench-verified: the real BSI sends exactly one frame with bit1=1
        # immediately after the mode change (0x87 for recirc, 0x07 for fresh),
        # which is what triggers the MFD popup "Cabin air recycling activated"
        # or "Forced intake of outside air".
        self.intake_notify = False
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
        self.spare = Tyres.OK
        self.pressure_fl = 2.4
        self.pressure_fr = 2.4
        self.pressure_rr = 2.2
        self.pressure_rl = 2.2
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
        # FM tuner state (used by the unified radio module and Msg225/Msg265/Msg2A5)
        # raw CAN freq value; display_MHz = freq * 0.05 + 50 (default 96.0 MHz)
        self.freq = 920
        self.band = 0x00      # 0x00=none; 0x10=FM1; 0x20=FM2; 0x40=FMAST; 0x50=AM
        self.mem = 0          # preset memory number (0 = none)
        self.rds = 0
        self.pty = 0
        self.ta = 0
        self.tun = 0
        self.scan = 0
        self.list_flag = 0
        self.tundir = 0
        self.station_name = 'test'
        self.rds_text = ''
        # Accumulation buffer for multi-frame RDS RadioText (0x0A4)
        # keyed by segment index → 7-char string
        self._rt_buf: dict = {}


class Trip:
    """Trip computer state."""

    def __init__(self):
        self.hide_fuel = 0
        self.hide_dist = 0
        self.com_left = 0
        self.com_right = 0
        self._com_left_ticks = 0
        self._com_right_ticks = 0
        self.fuel = 7.1
        self.autonomy = 740
        self.dist = 120
        # Two historical trip records, each with speed / dist / fuel fields.
        self.hist = [
            {'speed': 37, 'dist': 569, 'fuel': 7.3},
            {'speed': 35, 'dist': 921, 'fuel': 7.9},
        ]

    def press_com(self, button: str, ticks: int = 3) -> None:
        """Assert a stalk button for a pulse window of transmit cycles."""
        if button == 'com_right':
            self.com_right = 1
            self._com_right_ticks = ticks
        elif button == 'com_left':
            self.com_left = 1
            self._com_left_ticks = ticks

    def step_com_pulses(self) -> None:
        """Step down active stalk button pulse timers."""
        if self._com_right_ticks > 0:
            self._com_right_ticks -= 1
            if self._com_right_ticks == 0:
                self.com_right = 0
        if self._com_left_ticks > 0:
            self._com_left_ticks -= 1
            if self._com_left_ticks == 0:
                self.com_left = 0


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


class SteeringWheel:
    """Steering wheel, column stalks, and wheel angle state.

    The ``active`` flag is set by the ``steering_wheel`` (or ``buttons``)
    module when it loads.  When active, ``Msg1A5``, ``Msg21F``, ``Msg0C5``, and
    ``Msg3E5`` encode from this object, allowing the steering wheel subsystem
    to run independently of the head unit.

    Pulse-tick tracking keeps button press assertions alive for a few
    CAN frames (``_pulse_window`` encodes), matching the physical behaviour
    of momentary steering-wheel buttons.
    """

    BUTTON_KEYS = (
        'volume_up', 'volume_down', 'source', 'next', 'prev',
        'com_left', 'com_right',
    )

    REMOTE_ACTIONS = {
        'volume_up': 0x08,
        'volume_down': 0x04,
        'source': 0x02,
        'next': 0x80,
        'previous': 0x40,
        'prev': 0x40,
    }

    def __init__(self):
        self.active = False
        self.volume = 15
        # 0xE0 = stable; 0x00 = volume-change in progress
        self.volflag = 0xE0
        self._volume_action_ticks = 0
        self.panel = {k: 0 for k in self.BUTTON_KEYS}
        self._pulse_ticks = {k: 0 for k in self.BUTTON_KEYS}
        self._pulse_window = 3
        self.remote_action = None
        self.remote_aux = 0x09
        self._remote_pulse_ticks = 0
        # Steering wheel angle in degrees (-540.0° to +540.0°, centered at 0.0° by default)
        self.angle: float = 0.0

    def set_angle(self, angle: float) -> None:
        """Set the steering wheel angle in degrees."""
        self.angle = float(angle)

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

    def step_remote_pulses(self) -> bool:
        """Advance the steering-wheel remote pulse timer by one tick."""
        if self.remote_action is None:
            return False
        if self._remote_pulse_ticks > 0:
            self._remote_pulse_ticks -= 1
            if self._remote_pulse_ticks == 0:
                self.remote_action = None
                return True
        return False

    def press_remote(self, action: str) -> None:
        """Assert a steering-wheel remote action for a short pulse."""
        if action not in self.REMOTE_ACTIONS:
            return
        self.remote_action = action
        self.remote_aux = 0x09
        self._remote_pulse_ticks = self._pulse_window

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

    def pulse_volume(self, direction: str) -> None:
        """Convenience helper used by the buttons UI to trigger volume and remote frames."""
        if direction == 'up':
            self.volume_up()
            self.press_remote('volume_up')
        else:
            self.volume_down()
            self.press_remote('volume_down')


Buttons = SteeringWheel


class MFDPopup:
    """State for the BSI-log MFD popup messages (0x1A1 arbitration).

    The bsi-log module drives ``flag`` / ``msg_id`` through its state
    machine; the Msg1A1 message object reads from here to produce periodic
    transmissions.  When ``flag`` is 0xFF no popup is pending.
    """

    def __init__(self):
        self.flag = 0xFF   # 0xFF = inactive / no message pending
        self.msg_id = 0x00
        self.display_flags = 0xC6  # default display/priority flags for 0x1A1 byte2


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
        self.vin = self.bsi.vin
        self.clim = Clim()
        self.doors = Doors()
        self.parktronic = Parktronic()
        self.tyres = Tyres()
        self.dashboard = Dashboard()
        self.radio = Radio()
        self.trip = Trip()
        self.kml = KMLState()
        self.bte = BTEState()
        self.steering_wheel = SteeringWheel()
        self.buttons = self.steering_wheel
        self.mfd_popup = MFDPopup()
        self.speed_control = SpeedControl()

    @property
    def vin(self):
        return self.bsi.vin

    @vin.setter
    def vin(self, value):
        self.bsi.vin = str(value or 'VF3TEST1234567890')
