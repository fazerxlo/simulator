"""Auto-generated from signal-db/bsi.yaml — do not edit by hand.

BSI core messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


def _encode_oil_temp(temp_c: int) -> int:
    """Encode UI oil temperature using the workbench combine conversion.

    Bench observations indicate the combine does not visually track a simple
    raw = temperature + 40 mapping. A linear conversion fits the observed
    points and produces closer agreement on the physical cluster.
    """
    temp = int(temp_c)
    raw = round((79 * temp - 1360) / 50)
    return max(0x00, min(0xFE, raw))


def _decode_oil_temp(raw_value: int) -> int:
    """Decode received 0x161 oil temperature using the standard raw - 40 rule."""
    raw = int(raw_value) & 0xFF
    if raw == 0xFF:
        return 0
    return raw - 40


STARTUP_WAKEUP_BURST = [
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


class Msg0B6(CanMessage):
    """Fast dynamic data: engine RPM and vehicle speed.
    
    Workbench combine verification shows that bytes 0-1 carry RPM as a 13-bit
    raw value in bits 15..3, which is equivalent to displayed RPM shifted left
    by 3. Vehicle speed remains a uint16 scaled by 100.
    """

    can_id = 0x0B6
    period_ms = 50

    def encode(self, car) -> list:
        rpm = max(0, int(car.bsi.rpm)) << 3
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
        car.bsi.rpm = 0 if raw_rpm == 0xFFFF else (raw_rpm >> 3)
        car.bsi.speed = 0 if raw_speed == 0xFFFF else int(raw_speed / 100)
        car.bsi.engine_running = 1 if raw_rpm not in (0x0000, 0xFFFF) else 0


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


class Msg110(CanMessage):
    """BSI broadcast / presence frame."""

    can_id = 0x110
    period_ms = 100

    def encode(self, car) -> list:
        return [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00]


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
            cluster_on = 1 if (
                dash.on or car.bsi.ignition_on or int(car.bsi.power_mode) in (0x01, 0x03)
            ) else 0
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
            if dash.high_beam:
                car.bsi.light_mode = 3
            elif dash.low_beam:
                car.bsi.light_mode = 2
            elif dash.backlight:
                car.bsi.light_mode = 1
            else:
                car.bsi.light_mode = 0
            car.bsi.dash_lights = 1 if dash.backlight else 0
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


class Msg161(CanMessage):
    """BSI gauges: oil temperature, fuel level, oil level.
    
    Byte 2 is the oil-temperature source. Incoming frames decode using the
    standard raw - 40 protocol rule, while simulator-generated frames use a
    workbench-derived linear conversion so the physical combine display better
    matches the UI setpoint.
    """

    can_id = 0x161
    period_ms = 500

    def encode(self, car) -> list:
        oil_temp = _encode_oil_temp(car.bsi.oil)
        oil_level = int(car.bsi.oil_level) & 0xFF
        return [0x00, 0x00, oil_temp, int(car.bsi.fuel), 0xFF, 0xFF, oil_level]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 4:
            car.bsi.oil = _decode_oil_temp(data[2])
            car.bsi.fuel = int(data[3])
        if len(data) >= 7:
            car.bsi.oil_level = int(data[6])


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
    DOOR_DISPLAY_FLAGS = 0xC6
    DOOR_ANNOUNCE_FLAGS = 0xC6

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
            return [0x00, self.IDLE_MESSAGE_ID, self.DOOR_ANNOUNCE_FLAGS, 0x00, 0x00, 0x00, 0x00, 0x00]

        p = car.mfd_popup
        flag = 0x80 if p.flag == 0x80 else 0x00
        msg_id = p.msg_id if p.msg_id not in (None, 0x00) else self.IDLE_MESSAGE_ID
        return [flag, msg_id, p.display_flags, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 2:
            car.mfd_popup.flag = data[0]
            car.mfd_popup.msg_id = data[1]


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


class Msg217(CanMessage):
    """BSI status frame, content varies with ignition state."""

    can_id = 0x217
    period_ms = 100

    def encode(self, car) -> list:
        if car.bsi.power_mode == 0x01:
            return [0xA1, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xE0]
        return [0xA0, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00]


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


class Msg2B6(CanMessage):
    """VIN — Vehicle Indicator Section."""

    can_id = 0x2B6
    period_ms = 1000

    def encode(self, car) -> list:
        return [0x32, 0x31, 0x37, 0x31, 0x35, 0x33, 0x38, 0x33]


class Msg336(CanMessage):
    """VIN — World Manufacturer Identifier."""

    can_id = 0x336
    period_ms = 1000

    def encode(self, car) -> list:
        return [0x56, 0x46, 0x33]


class Msg3B6(CanMessage):
    """VIN — Vehicle Descriptor Section."""

    can_id = 0x3B6
    period_ms = 1000

    def encode(self, car) -> list:
        return [0x36, 0x4A, 0x52, 0x48, 0x52, 0x48]


class Msg52D(CanMessage):
    """BSI wake / sleep state frame."""

    can_id = 0x52D
    period_ms = 1000

    def encode(self, car) -> list:
        if car.bsi.power_mode == 0x01:
            return [0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00]
        return [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

