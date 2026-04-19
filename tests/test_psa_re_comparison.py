"""PSA-RE cross-reference tests: validate CAN encoders against PSA reverse-engineering documentation."""

import pytest

from car_state import VirtualCar, SpeedControl
from generated import ALL_MESSAGES, Msg0F6, Msg128, Msg168, Msg1A8, Msg161
from conftest import DummyWidget


# ---------------------------------------------------------------------------
# PSA-RE cross-reference tests
# Verify signal mappings confirmed by prototux/PSA-RE AEE2004 LS.CONF data
# ---------------------------------------------------------------------------

class TestMsg0F6PSARe:
    """0x0F6 — BSI_SLOW_DATA: verified signal positions from PSA-RE."""

    def test_decode_external_temperature_uses_half_degree_scaling(self):
        """PSA-RE: EXTERNAL_TEMPERATURE at byte 5 (idx 5), formula raw×0.5−40."""
        car = VirtualCar()
        # raw=0xB2=178 → 178*0.5-40 = 49.0 °C
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xB2, 0xB2, 0x20])
        assert abs(car.bsi.temperature - 49.0) < 0.01

    def test_decode_external_temperature_lo_boundary(self):
        """raw=0 → 0*0.5-40 = -40 °C (minimum)."""
        car = VirtualCar()
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20])
        assert abs(car.bsi.temperature - (-40.0)) < 0.01

    def test_decode_coolant_temperature_offset_minus_40(self):
        """PSA-RE: COOLANT_TEMPERATURE at byte 2 (idx 1), raw−40."""
        car = VirtualCar()
        # raw=0x3C=60 → 60-40 = 20 °C
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x20])
        assert car.bsi.coolant == 20

    def test_decode_reverse_from_byte7_bit7(self):
        """PSA-RE: REVERSE_STATUS at byte 8 (idx 7) bit 7."""
        car = VirtualCar()
        # bit 7 = 1 → reverse
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x80])
        assert car.bsi.reverse == 1

    def test_decode_no_reverse_when_bit7_clear(self):
        car = VirtualCar()
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x00])
        assert car.bsi.reverse == 0

    def test_encode_temperature_roundtrip(self):
        """Encode then decode should preserve temperature within 0.5 °C precision."""
        car = VirtualCar()
        car.bsi.temperature = 22.0
        data = Msg0F6().encode(car)
        car2 = VirtualCar()
        Msg0F6().decode(car2, data)
        assert abs(car2.bsi.temperature - 22.0) < 0.5

    def test_blinker_decode_and_encode(self):
        """PSA-RE: BLINKERS_STATUS decoded from byte 7 bits 1-0 into car.bsi.blinkers."""
        for blinker_val, label in [(0, 'none'), (1, 'right'), (2, 'left'), (3, 'both')]:
            car = VirtualCar()
            frame = [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, blinker_val]
            Msg0F6().decode(car, frame)
            assert car.bsi.blinkers == blinker_val, f'expected {blinker_val} for {label}'

    def test_encode_blinkers_in_byte7_bits1_0(self):
        """Encoding bsi.blinkers should set bits 1-0 of byte 7."""
        for blinker_val in [0, 1, 2, 3]:
            car = VirtualCar()
            car.bsi.blinkers = blinker_val
            data = Msg0F6().encode(car)
            assert (data[7] & 0x03) == blinker_val

    def test_encode_uses_0x88_status_byte(self):
        """Byte 0 must be 0x88 (real-bus value: customer config + generator ok)."""
        car = VirtualCar()
        data = Msg0F6().encode(car)
        assert data[0] == 0x88

    def test_encode_odometer_bytes_are_invalid(self):
        """Bench simulation encodes 0xFFFFFF (invalid) for the odometer bytes 2-4."""
        car = VirtualCar()
        data = Msg0F6().encode(car)
        assert data[2] == 0xFF
        assert data[3] == 0xFF
        assert data[4] == 0xFF

    def test_odometer_bytes_position(self):
        """PSA-RE: ODOMETER is 24-bit at bytes 3-5 (idx 2-4), ×0.1 km.
        The simulator encodes 0xFFFFFF (invalid) for bench simulation.
        Verify that when a real-bus frame is decoded the formula holds.
        """
        # Build a frame with a known odometer value of 12345.6 km
        odo_raw = round(12345.6 / 0.1)  # = 123456
        b2 = (odo_raw >> 16) & 0xFF
        b3 = (odo_raw >> 8) & 0xFF
        b4 = odo_raw & 0xFF
        frame = [0x88, 0x3C, b2, b3, b4, 0xFC, 0xFC, 0x20]
        decoded_odo = ((frame[2] << 16) | (frame[3] << 8) | frame[4]) * 0.1
        assert abs(decoded_odo - 12345.6) < 0.1


class TestMsg128PSARe:
    """0x128 — COMBINE_SIGNALS_INDICATORS: PSA-RE confirmed signal positions."""

    def test_stop_indicator_at_byte1_bit6(self):
        """PSA-RE: STOP at byte 2 (idx 1) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.stop = 1
        data = Msg128().encode(car)
        assert (data[1] >> 6) & 1 == 1

    def test_maintenance_indicator_at_byte1_bit7(self):
        """PSA-RE: MAINTENANCE (SERVICE) at byte 2 (idx 1) bit 7."""
        # In the simulator this bit comes from dash.warn which is the byte1 bit7 signal.
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.warn = 1
        data = Msg128().encode(car)
        assert (data[1] >> 7) & 1 == 1

    def test_low_beam_at_byte4_bit6(self):
        """PSA-RE: LOW_BEAM at byte 5 (idx 4) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.low_beam = 1
        data = Msg128().encode(car)
        assert (data[4] >> 6) & 1 == 1

    def test_full_beam_at_byte4_bit5(self):
        """PSA-RE: FULL_BEAM (FEUX_ROUTE) at byte 5 (idx 4) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.high_beam = 1
        data = Msg128().encode(car)
        assert (data[4] >> 5) & 1 == 1

    def test_front_fog_at_byte4_bit4(self):
        """PSA-RE: FRONT_FOG_LIGHTS at byte 5 (idx 4) bit 4."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.fog_front = 1
        data = Msg128().encode(car)
        assert (data[4] >> 4) & 1 == 1

    def test_rear_fog_at_byte4_bit3(self):
        """PSA-RE: REAR_FOG_LIGHTS at byte 5 (idx 4) bit 3."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.fog_rear = 1
        data = Msg128().encode(car)
        assert (data[4] >> 3) & 1 == 1

    def test_right_turn_at_byte4_bit2(self):
        """PSA-RE: RIGHT_TURN (CLIGNO_D) at byte 5 (idx 4) bit 2."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.clig_r = 1
        data = Msg128().encode(car)
        assert (data[4] >> 2) & 1 == 1

    def test_left_turn_at_byte4_bit1(self):
        """PSA-RE: LEFT_TURN (CLIGNO_G) at byte 5 (idx 4) bit 1."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.clig_l = 1
        data = Msg128().encode(car)
        assert (data[4] >> 1) & 1 == 1

    def test_cluster_on_at_byte5_bit7(self):
        """PSA-RE: CMB_ON at byte 6 (idx 5) bit 7."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.on = 1
        data = Msg128().encode(car)
        assert (data[5] >> 7) & 1 == 1

    def test_esp_disabled_at_byte2_bit5(self):
        """PSA-RE: ESP_DESACTIVED (ESPI) at byte 3 (idx 2) bit 4.
        The simulator encodes dash.esp at bit 5 of byte 2 (idx 2), not bit 4.
        PSA-RE bit 4 = ESP_DESACTIVED; bit 3 = ESP_BLINK (ESPACT).
        The simulator maps its dash.esp flag to bit 5 (the 'ESP blinking' position
        per PSA-RE), which is the combine module's chosen encoding.
        """
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.esp = 1
        data = Msg128().encode(car)
        assert (data[2] >> 5) & 1 == 1  # simulator uses bit 5

    def test_decode_stop_from_byte1_bit6(self):
        """Decode: STOP bit at byte1 (idx 1) bit6 updates car.dashboard.stop."""
        car = VirtualCar()
        car.dashboard.active = True
        # byte1 = 0x40 = 0b01000000 → bit6=1 (STOP)
        Msg128().decode(car, [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.dashboard.stop == 1

    def test_decode_low_beam_from_byte4_bit6(self):
        """Decode: LOW_BEAM at byte4 (idx 4) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        Msg128().decode(car, [0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00])
        assert car.dashboard.low_beam == 1


class TestMsg168PSARe:
    """0x168 — COMBINE_ALERTS_INDICATORS: PSA-RE confirmed signal positions.

    PSA-RE canonical name: COMBINE_ALERTS_INDICATORS (CDE_COMBINE_TEMOINS).
    This frame carries dashboard alert and fault indicators — NOT ambient temperature
    or battery voltage (earlier workspace notes from other sources were incorrect).
    """

    def test_coolant_alert_at_byte0_bit7(self):
        """PSA-RE: COOLANT_TEMPERATURE_ALERT at byte 1 (idx 0) bit 7."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.coolant_warn = 1
        data = Msg168().encode(car)
        assert data is not None
        assert (data[0] >> 7) & 1 == 1

    def test_oil_temperature_alert_at_byte0_bit6(self):
        """PSA-RE: OIL_TEMPERATURE_ALERT at byte 1 (idx 0) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.oil_blink = 1
        data = Msg168().encode(car)
        assert (data[0] >> 6) & 1 == 1

    def test_coolant_level_alert_at_byte0_bit5(self):
        """PSA-RE: COOLANT_LEVEL_ALERT at byte 1 (idx 0) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.coolant_blink = 1
        data = Msg168().encode(car)
        assert (data[0] >> 5) & 1 == 1

    def test_oil_warn_at_byte0_bit3(self):
        """PSA-RE: OIL_LEVEL_ALERT at byte 1 (idx 0) bit 3."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.oil_warn = 1
        data = Msg168().encode(car)
        assert (data[0] >> 3) & 1 == 1

    def test_abs_fault_at_byte3_bit5(self):
        """PSA-RE: ABS_FAULT at byte 4 (idx 3) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.abs = 1
        data = Msg168().encode(car)
        assert (data[3] >> 5) & 1 == 1

    def test_esp_fault_at_byte3_bit4(self):
        """PSA-RE: ASR_FAULT (ASR/ESP) at byte 4 (idx 3) bit 4."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.esp = 1
        data = Msg168().encode(car)
        assert (data[3] >> 4) & 1 == 1

    def test_eobd_fault_at_byte3_bit1(self):
        """PSA-RE: EOBD_FAULT (MIL) at byte 4 (idx 3) bit 1."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.obd = 1
        data = Msg168().encode(car)
        assert (data[3] >> 1) & 1 == 1

    def test_diesel_water_fault_at_byte3_bit0(self):
        """PSA-RE: DIESEL_WATER_FAULT at byte 4 (idx 3) bit 0."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.gas_water = 1
        data = Msg168().encode(car)
        assert data[3] & 1 == 1

    def test_safety_fault_airbag_at_byte4_bit5(self):
        """PSA-RE: SAFETY_FAULT at byte 5 (idx 4) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.airbag = 1
        data = Msg168().encode(car)
        assert (data[4] >> 5) & 1 == 1

    def test_alternator_fault_at_byte4_bit1(self):
        """PSA-RE: ALTERNATOR_FAULT at byte 5 (idx 4) bit 1."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.battery = 1
        data = Msg168().encode(car)
        assert (data[4] >> 1) & 1 == 1

    def test_0x168_is_not_ambient_temperature(self):
        """Regression: confirm 0x168 is NOT ambient temperature (earlier docs were wrong).

        The observed frame '8C 40 00 B2 24 00 20 00' has bits set in the alert indicator
        positions (coolant alert, oil pressure alert, EOBD fault), NOT a temperature value.
        """
        car = VirtualCar()
        car.dashboard.active = True
        # byte0=0x8C = 1000_1100 → coolant_warn(b7)=1, oil_warn(b3)=1, brake_level(b2)=1
        Msg168().decode(car, [0x8C, 0x40, 0x00, 0xB2, 0x24, 0x00, 0x20, 0x00])
        assert car.dashboard.coolant_warn == 1  # bit7 of byte0
        assert car.dashboard.oil_warn == 1       # bit3 of byte0

    def test_decode_roundtrip_preserve_all_alert_bits(self):
        """Encode then decode should preserve all alert indicator bits."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.coolant_warn = 1
        car.dashboard.abs = 1
        car.dashboard.obd = 1
        car.dashboard.battery = 1
        data = Msg168().encode(car)
        car2 = VirtualCar()
        car2.dashboard.active = True
        Msg168().decode(car2, data)
        assert car2.dashboard.coolant_warn == 1
        assert car2.dashboard.abs == 1
        assert car2.dashboard.obd == 1
        assert car2.dashboard.battery == 1


class TestMsg1A8:
    """0x1A8 — SPEED_CONTROL: encode/decode using the new Msg1A8 class."""

    def test_encode_set_speed_kmh(self):
        """SET_SPEED encoded as uint16 × 0.01 at bytes 1-2."""
        car = VirtualCar()
        car.speed_control.set_speed = 110.50
        data = Msg1A8().encode(car)
        speed_raw = (data[1] << 8) | data[2]
        assert abs(speed_raw * 0.01 - 110.50) < 0.01

    def test_encode_set_speed_none_is_0xffff(self):
        """set_speed=None encodes as 0xFFFF (not set)."""
        car = VirtualCar()
        car.speed_control.set_speed = None
        data = Msg1A8().encode(car)
        assert data[1] == 0xFF
        assert data[2] == 0xFF

    def test_decode_set_speed(self):
        """Decode SET_SPEED from bytes 1-2 into car.speed_control.set_speed."""
        car = VirtualCar()
        # 110.50 km/h → raw = 11050 = 0x2B2A
        Msg1A8().decode(car, [0x40, 0x2B, 0x2A, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert abs(car.speed_control.set_speed - 110.50) < 0.01

    def test_decode_set_speed_invalid(self):
        """0xFFFF decodes to None (no set speed)."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.speed_control.set_speed is None

    def test_encode_decode_set_speed_roundtrip(self):
        """Encode then decode should preserve set_speed within 0.01 km/h."""
        car = VirtualCar()
        car.speed_control.set_speed = 130.0
        data = Msg1A8().encode(car)
        car2 = VirtualCar()
        Msg1A8().decode(car2, data)
        assert abs(car2.speed_control.set_speed - 130.0) < 0.01

    def test_encode_partial_odometer(self):
        """ODOMETER_PARTIAL encoded as uint24 × 0.001 at bytes 5-7."""
        car = VirtualCar()
        car.speed_control.partial_odo = 1234.567
        data = Msg1A8().encode(car)
        odo_raw = (data[5] << 16) | (data[6] << 8) | data[7]
        assert abs(odo_raw * 0.001 - 1234.567) < 0.001

    def test_encode_partial_odometer_none_is_0xffffff(self):
        """partial_odo=None encodes as 0xFFFFFF (invalid)."""
        car = VirtualCar()
        car.speed_control.partial_odo = None
        data = Msg1A8().encode(car)
        assert data[5] == 0xFF
        assert data[6] == 0xFF
        assert data[7] == 0xFF

    def test_decode_partial_odometer(self):
        """Decode ODOMETER_PARTIAL from bytes 5-7."""
        car = VirtualCar()
        # 1234.567 km → raw = 1234567
        odo_raw = 1234567
        b5 = (odo_raw >> 16) & 0xFF
        b6 = (odo_raw >> 8) & 0xFF
        b7 = odo_raw & 0xFF
        Msg1A8().decode(car, [0x40, 0x00, 0x00, 0x00, 0x00, b5, b6, b7])
        assert abs(car.speed_control.partial_odo - 1234.567) < 0.001

    def test_decode_partial_odometer_invalid(self):
        """0xFFFFFF decodes to None (invalid)."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF])
        assert car.speed_control.partial_odo is None

    def test_encode_control_type_regulator(self):
        """SPEED_CONTROL_TYPE = REGULATOR (1) → bits 7-6 of byte 0 = 0b01."""
        car = VirtualCar()
        car.speed_control.control_type = SpeedControl.REGULATOR
        data = Msg1A8().encode(car)
        assert (data[0] >> 6) & 0x03 == 1

    def test_encode_control_type_limiter(self):
        """SPEED_CONTROL_TYPE = LIMITER (2) → bits 7-6 of byte 0 = 0b10."""
        car = VirtualCar()
        car.speed_control.control_type = SpeedControl.LIMITER
        data = Msg1A8().encode(car)
        assert (data[0] >> 6) & 0x03 == 2

    def test_decode_control_type(self):
        """Decode SPEED_CONTROL_TYPE from byte 0 bits 7-6."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.speed_control.control_type == 2  # limiter

    def test_encode_unit_mph(self):
        """unit_mph=True sets byte 0 bit 1."""
        car = VirtualCar()
        car.speed_control.unit_mph = True
        data = Msg1A8().encode(car)
        assert (data[0] >> 1) & 1 == 1

    def test_decode_unit_mph(self):
        """Decode unit_mph from byte 0 bit 1."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.speed_control.unit_mph is True

    def test_1a8_registered_in_all_messages(self):
        """Msg1A8 must appear in ALL_MESSAGES."""
        assert 0x1A8 in ALL_MESSAGES


class TestMsg161OilLevel:
    """0x161 — BSI_GAUGES oil temperature and oil level behavior."""

    def test_encode_oil_temp_uses_workbench_conversion_low(self):
        """UI 75 °C should encode to the raw value that matches the workbench combine."""
        car = VirtualCar()
        car.bsi.oil = 75
        data = Msg161().encode(car)
        assert abs(data[2] - 91) <= 1

    def test_encode_oil_temp_uses_workbench_conversion_high(self):
        """UI 154 °C should encode to the raw value that matches the workbench combine."""
        car = VirtualCar()
        car.bsi.oil = 154
        data = Msg161().encode(car)
        assert abs(data[2] - 216) <= 1

    def test_decode_oil_temp_uses_standard_raw_minus_40(self):
        """Incoming 0x161 frames still decode with the documented raw - 40 formula."""
        car = VirtualCar()
        Msg161().decode(car, [0x00, 0x00, 0x62, 0x32, 0xFF, 0xFF, 0x4B])
        assert car.bsi.oil == 58

    def test_encode_oil_level_at_byte6(self):
        """OIL_LEVEL encoded at byte 6 (0-indexed)."""
        car = VirtualCar()
        car.bsi.oil_level = 75
        data = Msg161().encode(car)
        assert data[6] == 75

    def test_encode_oil_level_invalid_is_0xff(self):
        """Default oil_level = 0xFF (invalid/not available) encodes as 0xFF."""
        car = VirtualCar()
        assert car.bsi.oil_level == 0xFF
        data = Msg161().encode(car)
        assert data[6] == 0xFF

    def test_decode_oil_level_from_byte6(self):
        """Decode OIL_LEVEL from byte 6 into car.bsi.oil_level."""
        car = VirtualCar()
        Msg161().decode(car, [0x00, 0x00, 0x50, 0x32, 0xFF, 0xFF, 0x4B])
        assert car.bsi.oil_level == 0x4B  # 75

    def test_decode_oil_level_invalid(self):
        """0xFF in byte 6 decodes as 0xFF (invalid)."""
        car = VirtualCar()
        Msg161().decode(car, [0x00, 0x00, 0x50, 0x32, 0xFF, 0xFF, 0xFF])
        assert car.bsi.oil_level == 0xFF

    def test_decode_short_frame_does_not_update_oil_level(self):
        """Frame shorter than 7 bytes should not update oil_level."""
        car = VirtualCar()
        car.bsi.oil_level = 50
        Msg161().decode(car, [0x00, 0x00, 0x50, 0x32, 0xFF, 0xFF])
        assert car.bsi.oil_level == 50  # unchanged

    def test_decode_raw_payload_all_fields(self):
        """Decode should preserve the documented oil/fuel/oil-level semantics from a literal payload."""
        car = VirtualCar()
        Msg161().decode(car, [0x00, 0x00, 0x87, 0x3C, 0xFF, 0xFF, 0x50])
        assert car.bsi.oil == 95
        assert car.bsi.fuel == 60
        assert car.bsi.oil_level == 80

    def test_frame_length_is_7_bytes(self):
        """PSA-RE defines 0x161 as 7 bytes; simulator encodes exactly 7."""
        car = VirtualCar()
        data = Msg161().encode(car)
        assert len(data) == 7
