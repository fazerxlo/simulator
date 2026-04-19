"""CAN message objects for the Peugeot 407 CAN2004 comfort bus (125 kbps).

Each class represents exactly one CAN arbitration ID.  Having a single
class per ID makes it impossible for two modules to accidentally register
conflicting senders for the same frame — the first caller that passes a
message object to ``runner.register_message()`` owns that ID.

Design principles
-----------------
* ``encode(car)`` builds the frame payload from ``VirtualCar`` state.
  Return ``None`` to suppress transmission this cycle.
* ``decode(car, data)`` updates ``VirtualCar`` state from a received frame.
* Stateful messages (e.g. rolling counter) may keep internal state on the
  object itself so that ``encode`` remains a pure function of *car* + *self*.
* Messages that belong to two logical subsystems (e.g. 0x128 which bsi-base
  sends in basic form but combine enhances) choose their encoding by
  inspecting a flag on the car state object (e.g. ``car.dashboard.active``).
"""

from __future__ import annotations


STARTUP_WAKEUP_BURST: list[tuple[float, int, list[int]]] = [
    (0.000, 0x5D2, [0xB0, 0x00, 0x00, 0x00, 0x01, 0x0A, 0x06, 0x16]),
    (0.010, 0x5ED, [0x2D, 0x09, 0x06, 0x04, 0x64, 0x05, 0x20, 0x0D]),
    (0.020, 0x5E5, [0x25, 0x09, 0x03, 0x05, 0x18, 0x08, 0x20, 0x11]),
    (0.030, 0x5CC, [0x0C, 0x19, 0x01, 0x06, 0x0A, 0x09, 0x20, 0x12]),
    (0.060, 0x5DF, [0x1F, 0x18, 0x09, 0x03, 0x08, 0x00, 0x20, 0x0D]),
    (0.090, 0x5F1, [0x31, 0x14, 0x08, 0x03, 0x05, 0x00, 0x20, 0x09]),
    (0.120, 0x5DD, [0x1D, 0x02, 0x06, 0x05, 0x02, 0x84, 0x20, 0x12]),
    (0.150, 0x48C, [0x50, 0xFC, 0x18, 0xFF, 0x04, 0x06, 0x07, 0x08]),
    (0.180, 0x5E0, [0x20, 0x1E, 0x03, 0x04, 0x05, 0x0E, 0x20, 0x0D]),
]


class CanMessage:
    """Base class for a periodic CAN message.

    Subclasses **must** set ``can_id`` and ``period_ms`` as class attributes
    and override ``encode``.  Overriding ``decode`` is optional but strongly
    recommended so that monitor mode and loopback testing work correctly.

    ``required_modules`` may be set to one or more config-module names.
    When non-empty, the runner only transmits this message while at least
    one of those modules is enabled in ``config.yml``.
    """

    #: CAN arbitration ID owned by this object.
    can_id: int = 0

    #: Transmit period in milliseconds.
    period_ms: int = 100

    #: Config-module names that must be enabled for this message to transmit.
    required_modules: frozenset[str] = frozenset()

    def get_period_ms(self, car) -> int:
        """Return the active transmit period for the current car state."""
        return self.period_ms

    def encode(self, car) -> list | None:
        """Build frame byte payload from car state.

        Return ``None`` to skip transmission this cycle.
        """
        return None

    def decode(self, car, data: bytes) -> None:
        """Update car state from a received frame with this *can_id*."""

    def __repr__(self) -> str:
        return f'{type(self).__name__}(can_id=0x{self.can_id:03X}, period_ms={self.period_ms})'


# ---------------------------------------------------------------------------
# 0x036 – COMMANDES_BSI (power mode, lights, economy, luminosity)
# ---------------------------------------------------------------------------

class Msg036(CanMessage):
    """BSI command frame: power mode, lighting, economy, dashboard luminosity."""

    can_id = 0x036
    period_ms = 100

    def __init__(self) -> None:
        self._boot_banner_sent = False

    def get_period_ms(self, car) -> int:
        if int(car.bsi.power_mode) == 0x02 and not car.bsi.ignition_on:
            return 175
        return 100

    def encode(self, car) -> list:
        bsi = car.bsi
        b2 = bsi.economy << 7
        b3 = bsi.dash_lights << 5 | bsi.dark_mode << 4 | (bsi.lum & 0x0F)
        b4 = bsi.power_mode
        pending_banner = bool(getattr(bsi, 'startup_banner_pending', False))
        trailer = 0x50 if pending_banner and not self._boot_banner_sent else 0xA0
        if pending_banner:
            bsi.startup_banner_pending = False
            self._boot_banner_sent = True
        return [0x0E, 0x00, b2, b3, b4, 0x00, 0x00, trailer]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 5:
            return
        car.bsi.economy = (data[2] >> 7) & 1
        car.bsi.dash_lights = (data[3] >> 5) & 1
        car.bsi.dark_mode = (data[3] >> 4) & 1
        car.bsi.lum = data[3] & 0x0F
        car.bsi.power_mode = data[4]
        car.bsi.ignition_on = (data[4] == 0x01)


# ---------------------------------------------------------------------------
# 0x0B6 – Fast dynamic data (RPM / Speed)
# ---------------------------------------------------------------------------

class Msg0B6(CanMessage):
    """Fast dynamic data: engine RPM and vehicle speed."""

    can_id = 0x0B6
    period_ms = 50

    def encode(self, car) -> list:
        rpm = int(car.bsi.rpm * 10)
        speed = int(car.bsi.speed * 100)
        if not car.bsi.ignition_on:
            return [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xD0]
        if rpm == 0 and speed == 0:
            return [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD0]
        return [rpm >> 8, rpm & 0xFF, speed >> 8, speed & 0xFF,
                0x00, 0x00, 0x00, 0xD0]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 4:
            return
        raw_rpm = (data[0] << 8) | data[1]
        raw_speed = (data[2] << 8) | data[3]

        # Real bench idle / engine-off traces use 0xFFFF placeholders rather
        # than literal sensor values. Treat those as invalid zeros so monitor
        # mode does not show absurd RPM or speed readings.
        car.bsi.rpm = 0 if raw_rpm == 0xFFFF else int(raw_rpm / 10)
        car.bsi.speed = 0 if raw_speed == 0xFFFF else int(raw_speed / 100)
        car.bsi.engine_running = 1 if raw_rpm not in (0x0000, 0xFFFF) else 0


# ---------------------------------------------------------------------------
# 0x0E1 – Parktronic sensor data
# ---------------------------------------------------------------------------

class Msg0E1(CanMessage):
    """Parking sensor distances and zone activation."""

    can_id = 0x0E1
    period_ms = 100
    required_modules = frozenset({'parktronic'})

    _INACTIVE = [0x24, 0x00, 0x3F, 0xFC, 0xFC, 0xFC, 0x00]

    def encode(self, car) -> list:
        p = car.parktronic
        if not p.display and not p.rear_active and not p.front_active:
            return list(self._INACTIVE)
        sensor_a = ((p.rear_left & 0x07) << 5) | ((p.rear_center & 0x07) << 2)
        sensor_b = ((p.rear_right & 0x07) << 5) | ((p.front_left & 0x07) << 2)
        sensor_c = ((p.front_center & 0x07) << 5) | ((p.front_right & 0x07) << 2) | 0x02
        zone = (0x40 if p.rear_active else 0x00) | (0x10 if p.front_active else 0x00)
        return [0x24, zone, 0x3F, sensor_a, sensor_b, sensor_c, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 6:
            return
        p = car.parktronic
        p.rear_active = (data[1] >> 6) & 1
        p.front_active = (data[1] >> 4) & 1
        p.display = 1 if (data[5] & 0x02) else 0
        p.rear_left = (data[3] >> 5) & 0x07
        p.rear_center = (data[3] >> 2) & 0x07
        p.rear_right = (data[4] >> 5) & 0x07
        p.front_left = (data[4] >> 2) & 0x07
        p.front_center = (data[5] >> 5) & 0x07
        p.front_right = (data[5] >> 2) & 0x07


# ---------------------------------------------------------------------------
# 0x0F6 – Slow dynamic data (coolant, exterior temp, reverse)
# ---------------------------------------------------------------------------

class Msg0F6(CanMessage):
    """BSI slow data: coolant/external temperature, odometer, reverse, blinkers.

    PSA-RE canonical name: ``BSI_SLOW_DATA`` / ``DONNEES_BSI_LENTES``.

    Byte layout (0-indexed):
      0  — status byte: ``0x88`` on real bus (customer config + generator ok + motor running)
      1  — coolant temperature: raw − 40 °C
      2-4 — odometer (uint24 × 0.1 km); simulator encodes ``0xFFFFFF`` (invalid) here
      5  — external temperature: raw × 0.5 − 40 °C (``0xFF`` = invalid)
      6  — external temperature filtered (same encoding as byte 5)
      7  — bit 7 = REVERSE_STATUS, bit 6 = FRONT_WIPERS_STATUS,
             bits 1-0 = BLINKERS_STATUS (0=none, 1=right, 2=left, 3=both)
    """

    can_id = 0x0F6
    period_ms = 500

    def encode(self, car) -> list:
        bsi = car.bsi
        temp = int((bsi.temperature + 40) * 2)
        coolant = int(bsi.coolant + 40)
        # byte 7: reverse + blinkers; force bit 0 high for compatibility
        b7 = (int(bsi.reverse) << 7) | (int(bsi.blinkers) & 0x03)
        # bytes 2-4: odometer — emit 0xFF FF FF (invalid) for bench simulation
        return [0x88, coolant, 0xFF, 0xFF, 0xFF, temp, temp, b7]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 8:
            return
        car.bsi.coolant = int(data[1]) - 40
        car.bsi.temperature = int(data[5]) / 2.0 - 40
        car.bsi.reverse = (data[7] >> 7) & 1
        car.bsi.blinkers = data[7] & 0x03


# ---------------------------------------------------------------------------
# 0x110 – Broadcast presence frame
# ---------------------------------------------------------------------------

class Msg110(CanMessage):
    """BSI broadcast / presence frame."""

    can_id = 0x110
    period_ms = 100

    def encode(self, car) -> list:
        return [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00]


# ---------------------------------------------------------------------------
# 0x12B – BTE module status
# ---------------------------------------------------------------------------

class Msg12B(CanMessage):
    """BTE module status byte."""

    can_id = 0x12B
    period_ms = 100
    required_modules = frozenset({'bte'})

    def encode(self, car) -> list:
        return [car.bte.bits]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            car.bte.bits = data[0]


# ---------------------------------------------------------------------------
# 0x12D – Climate controller command
# ---------------------------------------------------------------------------

class Msg12D(CanMessage):
    """Climate controller command (suppressed when ignition is off)."""

    can_id = 0x12D
    period_ms = 500
    required_modules = frozenset({'clim'})

    def encode(self, car) -> list | None:
        if not car.bsi.ignition_on:
            return None
        return [0x00, 0x32, 0x32, 0x00, 0x00, 0x00, 0x98, 0x80]


# ---------------------------------------------------------------------------
# 0x128 – Dashboard indicators
# ---------------------------------------------------------------------------

class Msg128(CanMessage):
    """Dashboard indicator lamps (0x128).

    When *car.dashboard.active* is ``True`` (combine module is loaded) the
    full instrument-cluster indicator set is encoded.  Otherwise the simpler
    BSI lighting-only encoding is used.
    """

    can_id = 0x128
    period_ms = 200

    _LIGHTS_TO_BYTE = {0: 0x00, 1: 0x80, 2: 0xC0, 3: 0xE0}

    def encode(self, car) -> list:
        if car.dashboard.active:
            dash = car.dashboard
            b0 = (dash.airbag_pass << 7 | dash.seatbelt << 6 | dash.brakes << 5 |
                  dash.low_fuel << 4 | dash.preheat << 2)
            b1 = dash.warn << 7 | dash.stop << 6 | dash.doors << 4
            b2 = dash.esp << 5 | dash.esp_blink << 4
            b3 = dash.tyre << 6
            b4 = (dash.backlight << 7 | dash.low_beam << 6 | dash.high_beam << 5 |
                  dash.fog_front << 4 | dash.fog_rear << 3 |
                  dash.clig_r << 2 | dash.clig_l << 1)
            cluster_on = 1 if (dash.on or car.bsi.ignition_on or int(car.bsi.power_mode) == 0x01) else 0
            # Keep the workbench cluster in the default manual-gearbox view
            # unless explicit gear-simulation fields are added later.
            gear_display = int(getattr(dash, 'gear_display', 0x00)) & 0xFF
            gearbox_mode = int(getattr(dash, 'gearbox_mode', 0x01)) & 0xFF
            b5 = cluster_on << 7
            return [b0, b1, b2, b3, b4, b5, gear_display, gearbox_mode]
        d5 = self._LIGHTS_TO_BYTE.get(car.bsi.light_mode, 0x00)
        return [0x91, 0xE0, 0x00, 0x00, d5, 0x80, 0xB0, 0x01]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 6:
            return
        if car.dashboard.active:
            dash = car.dashboard
            dash.airbag_pass = (data[0] >> 7) & 1
            dash.seatbelt = (data[0] >> 6) & 1
            dash.brakes = (data[0] >> 5) & 1
            dash.low_fuel = (data[0] >> 4) & 1
            dash.preheat = (data[0] >> 2) & 1
            dash.warn = (data[1] >> 7) & 1
            dash.stop = (data[1] >> 6) & 1
            dash.doors = (data[1] >> 4) & 1
            dash.esp = (data[2] >> 5) & 1
            dash.esp_blink = (data[2] >> 4) & 1
            dash.tyre = (data[3] >> 6) & 1
            dash.backlight = (data[4] >> 7) & 1
            dash.low_beam = (data[4] >> 6) & 1
            dash.high_beam = (data[4] >> 5) & 1
            dash.fog_front = (data[4] >> 4) & 1
            dash.fog_rear = (data[4] >> 3) & 1
            dash.clig_r = (data[4] >> 2) & 1
            dash.clig_l = (data[4] >> 1) & 1
            dash.on = (data[5] >> 7) & 1
        else:
            d5 = int(data[4]) & 0xE0
            if d5 & 0x20:
                car.bsi.light_mode = 3
            elif d5 & 0x40:
                car.bsi.light_mode = 2
            elif d5 & 0x80:
                car.bsi.light_mode = 1
            else:
                car.bsi.light_mode = 0


# ---------------------------------------------------------------------------
# 0x161 – Fuel and oil temperature levels
# ---------------------------------------------------------------------------

class Msg161(CanMessage):
    """BSI gauges: oil temperature, fuel level, oil level.

    PSA-RE canonical name: ``BSI_GAUGES`` / ``ETAT_BSI_TEMP_NIVEAU``.

    Byte layout (0-indexed):
      0  — OIL_LEVEL_RESTART flag (bit 7); simulator sends 0x00
      1  — unused
      2  — OIL_TEMPERATURE: raw − 40 °C (``0xFF`` = invalid)
      3  — FUEL_LEVEL: 0–100 % (``0xFF`` = invalid)
      4-5 — unused (``0xFF``)
      6  — OIL_LEVEL: 0–100 % (``0xFF`` = invalid/not available)
    """

    can_id = 0x161
    period_ms = 500

    def encode(self, car) -> list:
        oil_temp = int(car.bsi.oil + 40)
        oil_level = int(car.bsi.oil_level) & 0xFF
        return [0x00, 0x00, oil_temp, int(car.bsi.fuel), 0xFF, 0xFF, oil_level]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 4:
            car.bsi.oil = int(data[2]) - 40
            car.bsi.fuel = int(data[3])
        if len(data) >= 7:
            car.bsi.oil_level = int(data[6])


# ---------------------------------------------------------------------------
# 0x165 – Radio source / input status
# ---------------------------------------------------------------------------

class Msg165(CanMessage):
    """Radio source / input status."""

    can_id = 0x165
    period_ms = 50
    required_modules = frozenset({'radio-gen'})

    def encode(self, car) -> list:
        b2 = car.radio.INPUT_CODES.get(car.radio.input, 0x01) << 4
        return [0xCC, 0x54, b2, 0x02]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 3:
            return
        input_code = data[2] >> 4
        for name, code in car.radio.INPUT_CODES.items():
            if code == input_code:
                car.radio.input = name
                return


# ---------------------------------------------------------------------------
# 0x168 – Dashboard warning signals
# ---------------------------------------------------------------------------

class Msg168(CanMessage):
    """Dashboard warning / signal lamps (0x168).

    When *car.dashboard.active* is ``True`` (combine module loaded) the full
    warning-lamp set is encoded.  Otherwise only the tyre pressure overlay
    byte is included (when non-zero).
    """

    can_id = 0x168
    period_ms = 200

    def encode(self, car) -> list | None:
        if car.dashboard.active:
            dash = car.dashboard
            b0 = (dash.coolant_warn << 7 | dash.oil_blink << 6 |
                  dash.coolant_blink << 5 | dash.oil_warn << 3)
            tyre_overlay = int(car.tyres.alert_0x168_b1) & 0xC0
            b1 = tyre_overlay if tyre_overlay else (dash.tyre << 6)
            b3 = dash.abs << 5 | dash.esp << 4 | dash.obd << 1 | dash.gas_water
            b4 = dash.airbag << 5 | dash.battery << 1
            b6 = dash.dae << 5 | dash.eco_blink << 1 | dash.eco
            b7 = dash.battery_blink << 7 | dash.obd_blink << 6
            return [b0, b1, 0x00, b3, b4, 0x00, b6, b7]
        tyre_overlay = int(car.tyres.alert_0x168_b1) & 0xC0
        if not tyre_overlay:
            return None
        return [0x00, tyre_overlay, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 8 or not car.dashboard.active:
            return
        dash = car.dashboard
        dash.coolant_warn = (data[0] >> 7) & 1
        dash.oil_blink = (data[0] >> 6) & 1
        dash.coolant_blink = (data[0] >> 5) & 1
        dash.oil_warn = (data[0] >> 3) & 1
        dash.tyre = (data[1] >> 6) & 1
        dash.abs = (data[3] >> 5) & 1
        dash.esp = (data[3] >> 4) & 1
        dash.obd = (data[3] >> 1) & 1
        dash.gas_water = data[3] & 1
        dash.airbag = (data[4] >> 5) & 1
        dash.battery = (data[4] >> 1) & 1
        dash.dae = (data[6] >> 5) & 1
        dash.eco_blink = (data[6] >> 1) & 1
        dash.eco = data[6] & 1
        dash.battery_blink = (data[7] >> 7) & 1
        dash.obd_blink = (data[7] >> 6) & 1


# ---------------------------------------------------------------------------
# 0x190 – Status frame with rolling counter
# ---------------------------------------------------------------------------

class Msg190(CanMessage):
    """BSI status frame.  The low bit of byte 3 rolls when ignition is on."""

    can_id = 0x190
    period_ms = 200

    def __init__(self) -> None:
        self._rolling = 0

    def encode(self, car) -> list:
        if car.bsi.power_mode == 0x01:
            d4 = 0x7E | self._rolling
            self._rolling ^= 0x01
        else:
            d4 = 0x77
            self._rolling = 0
        return [0xFF, 0xFF, 0x02, d4, 0xFF, 0xFF, 0xFF, 0xFF]


# ---------------------------------------------------------------------------
# 0x1A1 – MFD popup / BSI log messages
# ---------------------------------------------------------------------------

class Msg1A1(CanMessage):
    """MFD popup message with dump-aligned PSA 0x1A1 formatting.

    Priority order (highest first):
    1. Tyre pressure warning  — ``car.tyres.display_active`` is True
    2. Door open warning      — ``car.doors.display_active`` is True
    3. BSI log popup / idle baseline frame

    The real bench captures keep 0x1A1 alive periodically even when no popup
    is actively shown. To match that behavior, this encoder now emits an idle
    baseline frame using message id ``0x8B`` and the observed display/priority
    byte ``0xC6`` whenever no higher-priority popup is active.
    """

    can_id = 0x1A1
    period_ms = 200
    IDLE_MESSAGE_ID = 0x8B
    DISPLAY_FLAGS = 0xC6
    DOOR_DISPLAY_FLAGS = 0xC7
    DOOR_ANNOUNCE_FLAGS = 0x47

    @staticmethod
    def _door_status_bytes(doors) -> tuple[int, int]:
        d3 = 0x00
        d4 = 0x00
        if doors.front_right:
            d3 |= 1 << 7
        if doors.front_left:
            d3 |= 1 << 6
        if doors.rear_right:
            d3 |= 1 << 5
        if doors.rear_left:
            d3 |= 1 << 4
        if doors.boot:
            d3 |= 1 << 3
        if doors.bonnet:
            d3 |= 1 << 2
        if doors.rear_window:
            d4 |= 1 << 7
        if doors.fuel_flap:
            d4 |= 1 << 6
        return d3, d4

    def encode(self, car) -> list | None:
        # Tyre warnings still own the bus with their dedicated event-driven payloads.
        if car.tyres.display_active:
            return None

        if car.doors.display_active:
            d = car.doors
            any_open = any((
                d.front_left, d.front_right, d.rear_left, d.rear_right,
                d.boot, d.bonnet, d.rear_window, d.fuel_flap,
            ))
            flag = 0x80 if any_open else 0xFF
            if d.front_left and not any((
                d.front_right, d.rear_left, d.rear_right,
                d.boot, d.bonnet, d.rear_window, d.fuel_flap,
            )):
                msg_id = 0xDE
            else:
                msg_id = d.popup_msg_id if d.popup_msg_id else 0x0B
            if any_open:
                d3, d4 = self._door_status_bytes(d)
                return [flag, msg_id, self.DOOR_DISPLAY_FLAGS, d3, d4, 0x00, 0x00, 0x00]
            return [0xFF, 0x00, self.DOOR_ANNOUNCE_FLAGS, 0x00, 0x00, 0x00, 0x00, 0x00]

        p = car.mfd_popup
        flag = 0x80 if p.flag == 0x80 else 0x00
        msg_id = p.msg_id if p.msg_id not in (None, 0x00) else self.IDLE_MESSAGE_ID
        return [flag, msg_id, p.display_flags, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 2:
            car.mfd_popup.flag = data[0]
            car.mfd_popup.msg_id = data[1]


# ---------------------------------------------------------------------------
# 0x1A3 – KML / hands-free phone status
# ---------------------------------------------------------------------------

class Msg1A3(CanMessage):
    """KML / hands-free phone module status."""

    can_id = 0x1A3
    period_ms = 100
    required_modules = frozenset({'kml'})

    def encode(self, car) -> list:
        return [0x80, car.kml.opt << 2, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 2:
            car.kml.opt = (data[1] >> 2) & 1


# ---------------------------------------------------------------------------
# 0x1A5 – Radio volume
# ---------------------------------------------------------------------------

class Msg1A5(CanMessage):
    """Radio / buttons volume level."""

    can_id = 0x1A5
    period_ms = 100
    required_modules = frozenset({'radio-gen', 'buttons', 'radio-cd'})

    def encode(self, car) -> list:
        if car.buttons.active:
            car.buttons.step_volume()
            return [car.buttons.volflag | (car.buttons.volume & 0x1F)]
        return [car.radio.volflag | (car.radio.volume & 0x1F)]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            volume = data[0] & 0x1F
            if car.buttons.active:
                car.buttons.volume = volume
            else:
                car.radio.volume = volume


# ---------------------------------------------------------------------------
# 0x1A8 – Speed control / cruise display
# ---------------------------------------------------------------------------

class Msg1A8(CanMessage):
    """Speed regulator / limiter and partial odometer (0x1A8).

    PSA-RE canonical name: ``SPEED_CONTROL`` / ``GESTION_VITESSE``.

    Byte layout (0-indexed):
      0  — bits 7-6: SPEED_CONTROL_TYPE (0=none, 1=regulator, 2=limiter, 3=adaptive)
             bits 5-3: ACTIVE_FUNCTION_STATUS (0=standby, 1=active, 2=limiter active,
                       3=overspeed no pedal, 4=overspeed with pedal, 6=not activatable, 7=fault)
             bit 2: ACTIVATION_ATTEMPT
             bit 1: CONTROL_UNIT (0=km/h, 1=mph)
      1-2 — SET_SPEED (uint16 × 0.01 km/h; 0xFFFF = not set)
      3-4 — unused (0x00)
      5-7 — ODOMETER_PARTIAL (uint24 × 0.001 km; 0xFFFFFF = invalid)
    """

    can_id = 0x1A8
    period_ms = 200

    def encode(self, car) -> list:
        sc = car.speed_control
        b0 = (
            ((sc.control_type & 0x03) << 6) |
            ((sc.function_status & 0x07) << 3) |
            ((sc.activation_attempt & 0x01) << 2) |
            ((int(sc.unit_mph) & 0x01) << 1)
        )
        # SET_SPEED
        if sc.set_speed is None:
            speed_raw = 0xFFFF
        else:
            speed_raw = min(0xFFFE, round(sc.set_speed / 0.01))
        b1 = (speed_raw >> 8) & 0xFF
        b2 = speed_raw & 0xFF
        # ODOMETER_PARTIAL
        if sc.partial_odo is None:
            odo_raw = 0xFFFFFF
        else:
            odo_raw = min(0xFFFFFE, round(sc.partial_odo / 0.001))
        b5 = (odo_raw >> 16) & 0xFF
        b6 = (odo_raw >> 8) & 0xFF
        b7 = odo_raw & 0xFF
        return [b0, b1, b2, 0x00, 0x00, b5, b6, b7]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 8:
            return
        sc = car.speed_control
        sc.control_type = (data[0] >> 6) & 0x03
        sc.function_status = (data[0] >> 3) & 0x07
        sc.activation_attempt = (data[0] >> 2) & 0x01
        sc.unit_mph = bool((data[0] >> 1) & 0x01)
        speed_raw = (data[1] << 8) | data[2]
        sc.set_speed = None if speed_raw == 0xFFFF else speed_raw * 0.01
        odo_raw = (data[5] << 16) | (data[6] << 8) | data[7]
        sc.partial_odo = None if odo_raw == 0xFFFFFF else odo_raw * 0.001


# ---------------------------------------------------------------------------
# Climate fan helper mapping
# ---------------------------------------------------------------------------


def _encode_clim_fan(fan_level: int) -> int:
    """Encode UI fan level 0-8 to the bench raw nibble used on 0x1D0 / 0x1E3.

    Real bench captures and PSA-RE show:
    - raw 0x0F = fan off
    - raw 0x00-0x07 = fan levels 1-8
    """
    level = max(0, min(8, int(fan_level)))
    return 0x0F if level == 0 else level - 1


def _decode_clim_fan(raw_value: int) -> int:
    """Decode the bench raw nibble to a UI fan level 0-8."""
    raw = int(raw_value) & 0x0F
    if raw == 0x0F:
        return 0
    if 0 <= raw <= 7:
        return raw + 1
    return 0


# ---------------------------------------------------------------------------
# 0x1D0 – Climate panel (BSI idle / full climate)
# ---------------------------------------------------------------------------

class Msg1D0(CanMessage):
    """Climate panel frame (0x1D0).

    Sends the BSI idle frame when the clim module is not loaded or ignition
    is off.  When ``car.clim.enabled`` is ``True`` and ignition is on, the
    full climate panel state is encoded instead.
    """

    can_id = 0x1D0
    period_ms = 500
    required_modules = frozenset({'clim'})

    def get_period_ms(self, car) -> int:
        return 500

    def encode(self, car) -> list:
        if not car.bsi.ignition_on:
            return [0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00]
        clim = car.clim
        if not clim.enabled:
            # Standby (fan=0, ignition on): climate suspended but ignition is on.
            # Workbench byte0=0xA8 (0x80|0x20|0x08); fan=0x0F; temps preserved.
            return [0xA8, 0x00, 0x0F, 0x00, 0x00, clim.temp_left, clim.temp_right, 0x00]
        dir_left = int(clim.dir_left) & 0x0F
        dir_right = int(clim.dir_right) & 0x0F
        dir_byte = (dir_left << 4) | dir_right
        if clim.unfrost_front:
            b0 = 0x19  # 0x08 | 0x11
        elif clim.auto or clim.intake_explicit:
            b0 = 0x08  # AUTO mode or explicit intake (recirc/fresh) — no manual-distribution bit
        else:
            b0 = 0x28  # 0x08 | 0x20 — manual fan/direction mode
        # Byte 4 bit layout (workbench-verified from clima_auto_inside_outside_auto.csv):
        #   bit5 (0x20): "explicit non-auto intake mode" — set when Fresh, Recirc, or
        #                UnfrostFront was actively selected by the user.
        #   bit4 (0x10): "recirculation" — set only when recirc is active.
        # AUTO mode: byte4=0x00; Fresh explicit: 0x20; Recirc explicit: 0x30.
        b4 = (0x20 if clim.intake_explicit else 0x00) | (0x10 if clim.recycle else 0x00)
        fan_raw = _encode_clim_fan(clim.fan)
        return [b0, 0x00, fan_raw, dir_byte, b4,
                clim.temp_left, clim.temp_right, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        car.clim.fan = _decode_clim_fan(data[2])
        raw_dir = data[3]
        high = (raw_dir >> 4) & 0x0F
        low = raw_dir & 0x0F
        # Real bench captures show 0x1D0 sometimes emits an ambiguous single-
        # nibble direction value (for example 0x04 while left=auto and right=up).
        # Only trust the classic mirrored-nibble format here, otherwise leave the
        # per-side airflow state to 0x1E3 which carries both zones explicitly.
        if high and high == low:
            car.clim.dir_left = high
        # bit4 = recirculation (workbench-verified); bit5 = non-auto intake flag.
        car.clim.recycle = (data[4] >> 4) & 1
        car.clim.temp_left = data[5]
        car.clim.temp_right = data[6]


# ---------------------------------------------------------------------------
# 0x1E3 – Climate EMF status
# ---------------------------------------------------------------------------

class Msg1E3(CanMessage):
    """Climate EMF status frame (0x1E3).

    Same conditional logic as :class:`Msg1D0`: uses the BSI standby frame
    unless ``car.clim.enabled`` is ``True`` and ignition is on.
    """

    can_id = 0x1E3
    period_ms = 200
    required_modules = frozenset({'clim'})

    def encode(self, car) -> list:
        if not car.bsi.ignition_on:
            return [0x1C, 0x40, 0x0B, 0x0B, 0x00, 0x00, 0x00, 0x00]
        clim = car.clim
        if not clim.enabled:
            # Standby (fan=0, ignition on): climate suspended but ignition is on.
            # Workbench byte0=(ac<<4)|0x20|dual; fan=0x0F; temps preserved.
            b1 = (clim.ac << 4) | 0x20 | clim.dual
            b2 = 0x30 | (clim.unfrost_front << 7)
            return [b1, b2, clim.temp_left, clim.temp_right, 0x00, 0x00, 0x0F, 0x00]
        # In AUTO mode bits 2+3 (0x0C) are set together; when an explicit
        # non-auto intake mode is active (Fresh/Recirc/UnfrostFront selected by
        # the user) bit2 (0x04) alone is set; in implicit manual mode both are
        # clear.  Bit 7 (0x80) is the recirculation indicator, set when
        # clim.recycle=1.
        # Verified against workbench:
        #   auto=1, ac=1, dual=0        → 0x1C
        #   auto=1, ac=1, dual=1        → 0x1D
        #   auto=0, ac=1, dual=1 (implicit fresh, from standby raise) → 0x11
        #   explicit fresh, ac=0, dual=1 → 0x05
        #   explicit recirc, ac=0, dual=1 → 0x85
        if clim.auto:
            mode_bits = 0x0C
        elif clim.intake_explicit:
            mode_bits = 0x04
        else:
            mode_bits = 0x00
        recirc_bit = 0x80 if clim.recycle else 0x00
        # Bit1 (0x02) is the one-shot MFD notification trigger: the real BSI
        # sets it for exactly one frame when switching to Recirc (→ popup
        # "Cabin air recycling activated") or Fresh (→ "Forced intake of
        # outside air").  Workbench: 0x87 = 0x85|0x02 on recirc entry,
        # 0x07 = 0x05|0x02 on fresh entry.
        notify_bit = 0x02 if clim.intake_notify else 0x00
        clim.intake_notify = False  # one-shot: consume after first use
        # Workbench: recirc and explicit-fresh always encode ac=0 in byte0
        # (verified from workbench captures: 0x85 for recirc, 0x05 for fresh).
        # AUTO mode and unfrost_front preserve the user's A/C setting (clim.ac).
        # This keeps the simulator A/C button state independent of airflow mode.
        if clim.auto or clim.unfrost_front or not clim.intake_explicit:
            ac_enc = clim.ac
        else:
            ac_enc = 0
        b1 = recirc_bit | (ac_enc << 4) | mode_bits | notify_bit | clim.dual
        b2 = 0x30 | (clim.unfrost_front << 7)
        b3 = clim.bits | clim.temp_left
        b4 = clim.temp_right
        b5 = clim.dir_left << 4
        b6 = clim.dir_right << 4
        b7 = _encode_clim_fan(clim.fan)
        return [b1, b2, b3, b4, b5, b6, b7, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        car.clim.fan = _decode_clim_fan(data[6])
        car.clim.dir_left = data[4] >> 4
        car.clim.dir_right = data[5] >> 4
        car.clim.ac = (data[0] >> 4) & 1
        car.clim.auto = (data[0] >> 3) & 1
        car.clim.dual = data[0] & 1
        # bit7 of byte0 = recirculation indicator (workbench-verified).
        car.clim.recycle = (data[0] >> 7) & 1
        car.clim.unfrost_front = (data[1] >> 7) & 1
        car.clim.temp_left = data[2] & 0x1F
        car.clim.temp_right = data[3]


# ---------------------------------------------------------------------------
# 0x1E5 – Radio audio settings
# ---------------------------------------------------------------------------

class Msg1E5(CanMessage):
    """Radio audio settings: balance, bass, treble, loudness, ambiance."""

    can_id = 0x1E5
    period_ms = 100
    required_modules = frozenset({'radio-gen'})

    _AMBIANCE_CODES = {
        'none': 0x03, 'classical': 0x07, 'jazz-blues': 0x0B,
        'pop-rock': 0x0F, 'vocal': 0x13, 'techno': 0x17,
    }

    def encode(self, car) -> list:
        a = car.radio.audio
        b0 = (1 << 7 if a['menu'] == 'lr-bal' else 0) | (a['lr-bal'] & 0x7F)
        b1 = (1 << 7 if a['menu'] == 'rf-bal' else 0) | (a['rf-bal'] & 0x7F)
        b2 = (1 << 7 if a['menu'] == 'bass' else 0) | (a['bass'] & 0x7F)
        b4 = (1 << 7 if a['menu'] == 'treble' else 0) | (a['treble'] & 0x7F)
        b5 = ((1 << 7 if a['menu'] == 'loudness' else 0) |
              (a['loudness'] << 6) |
              (1 << 4 if a['menu'] == 'volume' else 0) |
              (a['volume'] & 0x0F))
        b6 = ((1 << 6 if a['menu'] == 'ambiance' else 0) |
              self._AMBIANCE_CODES.get(a['ambiance'], 0x03))
        return [b0, b1, b2, 0x00, b4, b5, b6]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        a = car.radio.audio
        if data[0] & 0x80:
            a['menu'] = 'lr-bal'
            a['lr-bal'] = data[0] & 0x7F
        elif data[1] & 0x80:
            a['menu'] = 'rf-bal'
            a['rf-bal'] = data[1] & 0x7F
        elif data[2] & 0x80:
            a['menu'] = 'bass'
            a['bass'] = data[2] & 0x7F
        elif data[4] & 0x80:
            a['menu'] = 'treble'
            a['treble'] = data[4] & 0x7F
        elif data[5] & 0x10:
            a['menu'] = 'volume'
            a['volume'] = data[5] & 0x0F
        elif data[5] & 0x40:
            a['menu'] = 'loudness'
            a['loudness'] = (data[5] >> 6) & 1
        elif data[6] & 0x40:
            a['menu'] = 'ambiance'
            target = data[6] & 0x3F
            for name, code in self._AMBIANCE_CODES.items():
                if code == target:
                    a['ambiance'] = name
                    break


# ---------------------------------------------------------------------------
# 0x217 – BSI status (varies with ignition state)
# ---------------------------------------------------------------------------

class Msg217(CanMessage):
    """BSI status frame, content varies with ignition state."""

    can_id = 0x217
    period_ms = 100

    def encode(self, car) -> list:
        if car.bsi.power_mode == 0x01:
            return [0xA1, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xE0]
        return [0xA0, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00]


# ---------------------------------------------------------------------------
# 0x220 – Door open status
# ---------------------------------------------------------------------------

class Msg220(CanMessage):
    """Door open/closed status byte."""

    can_id = 0x220
    period_ms = 100

    def encode(self, car) -> list:
        d = car.doors
        b0 = (d.front_left << 7 | d.front_right << 6 | d.rear_left << 5 |
              d.rear_right << 4 | d.boot << 3 | d.bonnet << 2 |
              d.rear_window << 1 | d.fuel_flap)
        return [b0, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 1:
            return
        b0 = data[0]
        car.doors.front_left = (b0 >> 7) & 1
        car.doors.front_right = (b0 >> 6) & 1
        car.doors.rear_left = (b0 >> 5) & 1
        car.doors.rear_right = (b0 >> 4) & 1
        car.doors.boot = (b0 >> 3) & 1
        car.doors.bonnet = (b0 >> 2) & 1
        car.doors.rear_window = (b0 >> 1) & 1
        car.doors.fuel_flap = b0 & 1


# ---------------------------------------------------------------------------
# 0x221 – Trip computer instantaneous data
# ---------------------------------------------------------------------------

class Msg221(CanMessage):
    """Trip computer: instantaneous fuel consumption, autonomy, distance."""

    can_id = 0x221
    period_ms = 1000
    required_modules = frozenset({'bsi-trip'})

    def encode(self, car) -> list:
        t = car.trip
        b0 = t.hide_fuel << 7 | t.hide_dist << 6 | t.com_right << 3 | t.com_left
        fuel = int(t.fuel * 10)
        autonomy = int(t.autonomy)
        distance = int(t.dist * 10)
        return [b0, fuel >> 8, fuel & 0xFF,
                autonomy >> 8, autonomy & 0xFF,
                distance >> 8, distance & 0xFF]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        t = car.trip
        t.hide_fuel = (data[0] >> 7) & 1
        t.hide_dist = (data[0] >> 6) & 1
        t.com_right = (data[0] >> 3) & 1
        t.com_left = data[0] & 1
        t.fuel = ((data[1] << 8) | data[2]) / 10.0
        t.autonomy = (data[3] << 8) | data[4]
        t.dist = ((data[5] << 8) | data[6]) / 10.0


# ---------------------------------------------------------------------------
# 0x223 – KML data frame
# ---------------------------------------------------------------------------

class Msg223(CanMessage):
    """KML module data frame."""

    can_id = 0x223
    period_ms = 100
    required_modules = frozenset({'kml'})

    def encode(self, car) -> list:
        return [car.kml.bits_223, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            car.kml.bits_223 = data[0]


# ---------------------------------------------------------------------------
# 0x2A1 – Trip computer history record 1
# ---------------------------------------------------------------------------

class Msg2A1(CanMessage):
    """Trip computer historical record 1."""

    can_id = 0x2A1
    period_ms = 1000
    required_modules = frozenset({'bsi-trip'})

    def encode(self, car) -> list:
        hist = car.trip.hist[0]
        dist = int(hist['dist'])
        fuel = int(hist['fuel'] * 10)
        return [int(hist['speed']), dist >> 8, dist & 0xFF,
                fuel >> 8, fuel & 0xFF, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 5:
            h = car.trip.hist[0]
            h['speed'] = data[0]
            h['dist'] = (data[1] << 8) | data[2]
            h['fuel'] = ((data[3] << 8) | data[4]) / 10.0


# ---------------------------------------------------------------------------
# 0x261 – Trip computer history record 2
# ---------------------------------------------------------------------------

class Msg261(CanMessage):
    """Trip computer historical record 2."""

    can_id = 0x261
    period_ms = 1000
    required_modules = frozenset({'bsi-trip'})

    def encode(self, car) -> list:
        hist = car.trip.hist[1]
        dist = int(hist['dist'])
        fuel = int(hist['fuel'] * 10)
        return [int(hist['speed']), dist >> 8, dist & 0xFF,
                fuel >> 8, fuel & 0xFF, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 5:
            h = car.trip.hist[1]
            h['speed'] = data[0]
            h['dist'] = (data[1] << 8) | data[2]
            h['fuel'] = ((data[3] << 8) | data[4]) / 10.0


# ---------------------------------------------------------------------------
# 0x2B6 – VIN VIS (Vehicle Indicator Section)
# ---------------------------------------------------------------------------

class Msg2B6(CanMessage):
    """VIN — Vehicle Indicator Section."""

    can_id = 0x2B6
    period_ms = 1000

    def encode(self, car) -> list:
        return [0x32, 0x31, 0x37, 0x31, 0x35, 0x33, 0x38, 0x33]


# ---------------------------------------------------------------------------
# 0x323 – KML data frame 2
# ---------------------------------------------------------------------------

class Msg323(CanMessage):
    """KML module data frame 2 (mostly fixed content)."""

    can_id = 0x323
    period_ms = 100
    required_modules = frozenset({'kml'})

    _FIXED = [0x66, 0x08, 0x68, 0x00, 0x02, 0x02, 0x00]

    def encode(self, car) -> list:
        return list(self._FIXED)

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            car.kml.bits_323 = data[0]


# ---------------------------------------------------------------------------
# 0x336 – VIN WMI (World Manufacturer Identifier)
# ---------------------------------------------------------------------------

class Msg336(CanMessage):
    """VIN — World Manufacturer Identifier."""

    can_id = 0x336
    period_ms = 1000

    def encode(self, car) -> list:
        return [0x56, 0x46, 0x33]


# ---------------------------------------------------------------------------
# 0x3B6 – VIN VDS (Vehicle Descriptor Section)
# ---------------------------------------------------------------------------

class Msg3B6(CanMessage):
    """VIN — Vehicle Descriptor Section."""

    can_id = 0x3B6
    period_ms = 1000

    def encode(self, car) -> list:
        return [0x36, 0x4A, 0x52, 0x48, 0x52, 0x48]


# ---------------------------------------------------------------------------
# 0x3E5 – Steering wheel panel buttons
# ---------------------------------------------------------------------------

class Msg3E5(CanMessage):
    """Steering wheel control panel buttons.

    Encodes from ``car.buttons`` when the ``buttons`` module is active
    (different bit layout and key set); otherwise encodes from
    ``car.radio.panel`` for ``radio-gen`` / ``radio-cd``.
    """

    can_id = 0x3E5
    period_ms = 50
    required_modules = frozenset({'radio-gen', 'buttons', 'radio-cd'})

    def encode(self, car) -> list:
        if car.buttons.active:
            p = car.buttons.panel
            car.buttons.step_pulses()
            b0 = (p['tel'] << 4) | p['clima']
            b1 = (p['trip'] << 6) | (p['source'] << 4) | p['dark']
            b2 = (p['ok'] << 6) | (p['esc'] << 4) | (p['next'] << 2) | p['prev']
            b5 = (p['up'] << 6) | (p['down'] << 4) | (p['right'] << 2) | p['left']
            return [b0, b1, b2, 0x00, 0x00, b5]
        k = car.radio.panel
        b0 = k['menu'] << 6 | k['tel'] << 4 | k['clim']
        b1 = k['trip'] << 6 | k['mode'] << 4 | k['audio']
        b2 = k['ok'] << 6 | k['esc'] << 4
        b5 = k['up'] << 6 | k['down'] << 4 | k['right'] << 2 | k['left']
        return [b0, b1, b2, 0x00, 0x00, b5]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 6:
            return
        if car.buttons.active:
            b0, b1, b2 = data[0], data[1], data[2]
            b5 = data[5]
            car.buttons.panel['tel'] = (b0 >> 4) & 1
            car.buttons.panel['clima'] = b0 & 1
            car.buttons.panel['trip'] = (b1 >> 6) & 1
            car.buttons.panel['source'] = (b1 >> 4) & 1
            car.buttons.panel['dark'] = b1 & 1
            car.buttons.panel['ok'] = (b2 >> 6) & 1
            car.buttons.panel['esc'] = (b2 >> 4) & 1
            car.buttons.panel['next'] = (b2 >> 2) & 1
            car.buttons.panel['prev'] = b2 & 1
            car.buttons.panel['up'] = (b5 >> 6) & 1
            car.buttons.panel['down'] = (b5 >> 4) & 1
            car.buttons.panel['right'] = (b5 >> 2) & 1
            car.buttons.panel['left'] = b5 & 1
            return
        b0, b1, b2 = data[0], data[1], data[2]
        b5 = data[5]
        car.radio.panel['menu'] = (b0 >> 6) & 1
        car.radio.panel['tel'] = (b0 >> 4) & 1
        car.radio.panel['clim'] = b0 & 1
        car.radio.panel['trip'] = (b1 >> 6) & 1
        car.radio.panel['mode'] = (b1 >> 4) & 1
        car.radio.panel['audio'] = b1 & 1
        car.radio.panel['ok'] = (b2 >> 6) & 1
        car.radio.panel['esc'] = (b2 >> 4) & 1
        car.radio.panel['up'] = (b5 >> 6) & 1
        car.radio.panel['down'] = (b5 >> 4) & 1
        car.radio.panel['right'] = (b5 >> 2) & 1
        car.radio.panel['left'] = b5 & 1


# ---------------------------------------------------------------------------
# 0x52D – BSI wake/sleep frame
# ---------------------------------------------------------------------------

class Msg52D(CanMessage):
    """BSI wake / sleep state frame."""

    can_id = 0x52D
    period_ms = 1000

    def encode(self, car) -> list:
        if car.bsi.power_mode == 0x01:
            return [0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00]
        return [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]


# ---------------------------------------------------------------------------
# Convenience registry: all well-known message classes keyed by CAN ID.
# ---------------------------------------------------------------------------

#: Maps CAN arbitration IDs to their :class:`CanMessage` subclass.
ALL_MESSAGES: dict[int, type] = {
    cls.can_id: cls
    for cls in (
        Msg036, Msg0B6, Msg0E1, Msg0F6, Msg110, Msg12B, Msg12D,
        Msg128, Msg161, Msg165, Msg168, Msg190, Msg1A1, Msg1A3,
        Msg1A5, Msg1A8, Msg1D0, Msg1E3, Msg1E5, Msg217, Msg220, Msg221,
        Msg223, Msg2A1, Msg261, Msg2B6, Msg323, Msg336, Msg3B6,
        Msg3E5, Msg52D,
    )
}
