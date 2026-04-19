"""AWP workbench comparison tests: validate CAN encoders against real bench captures."""

import pytest

from car_state import VirtualCar
from generated import Msg0B6, Msg0F6, Msg128, Msg1D0


# ---------------------------------------------------------------------------
# autowp cross-reference tests
# Verify simulator signals against the autowp.github.io community documentation.
# See doc/CAN2004_autowp_comparison.md for the full analysis.
# ---------------------------------------------------------------------------

class TestMsg0B6AwpCompare:
    """0x0B6 — workbench-verified RPM/Speed encoding.

    The workbench combine expects RPM as a 13-bit raw value packed into bits
    15..3 of bytes 0-1, i.e. displayed RPM shifted left by 3. Speed remains a
    16-bit integer scaled by 100.
    """

    def test_encode_rpm_uses_shifted_raw_scaling(self):
        """Workbench combine expects RPM encoded as rpm << 3."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 800
        data = Msg0B6().encode(car)
        raw_rpm = (data[0] << 8) | data[1]
        assert raw_rpm == (800 << 3)

    def test_encode_speed_uses_times_hundred_scaling(self):
        """Speed is encoded as integer(speed × 100) in a 16-bit big-endian word.
        autowp confirms this: 'actual speed * 100 in km/h'.
        """
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.speed = 120
        data = Msg0B6().encode(car)
        raw_speed = (data[2] << 8) | data[3]
        assert raw_speed == 12000  # 120 × 100

    def test_encode_byte7_is_constant_d0(self):
        """autowp confirms byte 7 = 0xD0 (constant 0b11010000)."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 800
        car.bsi.speed = 50
        data = Msg0B6().encode(car)
        assert data[7] == 0xD0

    def test_encode_byte7_d0_present_when_ignition_off(self):
        """Byte 7 constant 0xD0 is present even in the 'ignition off' placeholder frame."""
        car = VirtualCar()
        car.bsi.ignition_on = False
        data = Msg0B6().encode(car)
        assert data[7] == 0xD0

    def test_decode_roundtrip_rpm_and_speed(self):
        """Encode then decode should preserve RPM and speed."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 1500
        car.bsi.speed = 90
        data = Msg0B6().encode(car)
        car2 = VirtualCar()
        Msg0B6().decode(car2, data)
        assert car2.bsi.rpm == 1500
        assert car2.bsi.speed == 90

    def test_decode_accepts_workbench_shifted_rpm_payload(self):
        """A raw workbench payload with rpm << 3 decodes to the displayed RPM."""
        car = VirtualCar()
        Msg0B6().decode(car, [0x19, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD0])
        assert car.bsi.rpm == 800
        assert car.bsi.engine_running == 1

    def test_decode_sets_engine_running_when_rpm_nonzero(self):
        """engine_running flag should be set from RPM field."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 800
        data = Msg0B6().encode(car)
        car2 = VirtualCar()
        Msg0B6().decode(car2, data)
        assert car2.bsi.engine_running == 1

    def test_decode_clears_engine_running_when_rpm_zero(self):
        car = VirtualCar()
        # Explicitly feed a frame with raw RPM = 0x0000 (engine off, not a placeholder)
        Msg0B6().decode(car, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD0])
        assert car.bsi.engine_running == 0


class TestMsg0F6AwpCompare:
    """0x0F6 — autowp cross-reference for temperature and reverse signals.

    Tests verify the simulator's PSA-RE temperature byte layout (byte 5 for
    external temperature, raw × 0.5 − 40 °C) and confirm differences from
    autowp documentation (which places external temperature at byte 6 and
    claims byte 5 is a constant 0x8E).  The PSA-RE layout is authoritative,
    confirmed by real-bus captures in CAN2004_cold_start.md.
    """

    def test_encode_status_byte_is_0x88(self):
        """Simulator encodes 0x88 (customer config + generator ok), matching real bus.
        autowp documents a different interpretation of byte 0 but the value 0x88
        is confirmed by real-bus captures in CAN2004_cold_start.md.
        """
        car = VirtualCar()
        data = Msg0F6().encode(car)
        assert data[0] == 0x88

    def test_encode_external_temp_at_byte5_not_constant(self):
        """PSA-RE places EXTERNAL_TEMPERATURE at byte 5 (idx 4 in 0-indexed).
        autowp claims byte 5 is constant 0x8E for some trim variants.
        The PSA-RE position is verified by real-bus captures; byte 5 must
        carry the encoded temperature, not a constant.
        """
        car = VirtualCar()
        car.bsi.temperature = 20.0  # 20 °C → raw = (20+40)*2 = 120 = 0x78
        data = Msg0F6().encode(car)
        assert data[5] == 0x78
        assert data[5] != 0x8E  # must not be autowp's claimed constant

    def test_decode_external_temp_from_byte5(self):
        """External temperature must decode from byte 5, not byte 6."""
        car = VirtualCar()
        # byte 5 = 0x78 → 120 × 0.5 − 40 = 20.0 °C
        # byte 6 = 0x8E (autowp's alleged constant for byte 5)
        Msg0F6().decode(car, [0x88, 0x3C, 0xFF, 0xFF, 0xFF, 0x78, 0x8E, 0x00])
        assert abs(car.bsi.temperature - 20.0) < 0.01

    def test_coolant_formula_raw_minus_40(self):
        """PSA-RE coolant formula is raw − 40.  autowp says C − 39.
        The simulator uses raw − 40 (PSA-RE authoritative).
        """
        car = VirtualCar()
        # raw coolant = 0x3C = 60 → 60 − 40 = 20 °C (PSA-RE)
        Msg0F6().decode(car, [0x88, 0x3C, 0xFF, 0xFF, 0xFF, 0xFC, 0xFC, 0x00])
        assert car.bsi.coolant == 20  # PSA-RE: raw − 40


class TestMsg128AwpCompare:
    """0x128 — autowp cross-reference for lighting signals.

    autowp confirms the byte 4 lighting signal positions independently of
    PSA-RE.  Tests here exercise the sidelights signal (backlight flag) which
    is present in autowp but was not covered by the existing PSA-RE test class.
    """

    def test_sidelights_at_byte4_bit7_when_dashboard_active(self):
        """autowp: 'G = sidelights on' at byte 4 bit 7.
        PSA-RE: SIDELIGHTS (FEUX_POS) at byte 5 (idx 4) bit 7.
        Simulator: dash.backlight mapped to byte 4 bit 7.
        """
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.backlight = 1
        data = Msg128().encode(car)
        assert (data[4] >> 7) & 1 == 1

    def test_sidelights_absent_when_backlight_zero(self):
        """Sidelights bit must be 0 when backlight is off."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.backlight = 0
        data = Msg128().encode(car)
        assert (data[4] >> 7) & 1 == 0

    def test_decode_sidelights_from_byte4_bit7(self):
        """Sidelights decoded from byte 4 bit 7 into car.dashboard.backlight."""
        car = VirtualCar()
        car.dashboard.active = True
        Msg128().decode(car, [0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00])
        assert car.dashboard.backlight == 1

    def test_all_lighting_bits_in_byte4_match_autowp(self):
        """Verify all seven lighting bits in byte 4 match autowp positions.

        autowp byte 4 layout (MSB first):
          bit 7 = G (sidelights), bit 6 = F (low beam), bit 5 = E (high beam),
          bit 4 = D (front fog), bit 3 = C (rear fog), bit 2 = B (right turn),
          bit 1 = A (left turn)
        """
        fields = [
            ('backlight', 7, 'sidelights'),
            ('low_beam',  6, 'low beam'),
            ('high_beam', 5, 'high beam'),
            ('fog_front', 4, 'front fog'),
            ('fog_rear',  3, 'rear fog'),
            ('clig_r',    2, 'right indicator'),
            ('clig_l',    1, 'left indicator'),
        ]
        for attr, bit, name in fields:
            car = VirtualCar()
            car.dashboard.active = True
            setattr(car.dashboard, attr, 1)
            data = Msg128().encode(car)
            assert (data[4] >> bit) & 1 == 1, f'{name} (bit {bit}) not set'


class TestMsg1D0AwpCompare:
    """0x1D0 — bench-aligned climate panel encoding.

    Bench captures show byte 3 carries independent left and right zone
    directions as (dir_left << 4) | dir_right, matching the 0x1E3 per-zone
    layout.  The earlier repeated-nibble format (dir_left mirrored) has been
    corrected.
    """

    def test_fan_speed_encoded_as_bench_aligned_nibble_value(self):
        """Bench and PSA-RE agree: byte 2 low nibble uses 0-7 for fan 1-8 and 0x0F for off.
        So internal fan=3 should encode as raw 0x02.
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.fan = 3
        data = Msg1D0().encode(car)
        assert data[2] == 0x02

    def test_recirc_byte4_is_0x30_when_intake_explicit(self):
        """Workbench: recirc mode → byte4=0x30 (bit5=non-auto, bit4=recirc)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert data[4] == 0x30  # 0x20 (non-auto intake) | 0x10 (recirc)

    def test_fresh_explicit_byte4_is_0x20(self):
        """Workbench: explicitly pressing Fresh → byte4=0x20 (non-auto flag, no recirc)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.recycle = 0
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert data[4] == 0x20  # 0x20 (non-auto intake) | 0x00 (no recirc)

    def test_auto_mode_byte4_is_0x00(self):
        """Workbench: AUTO mode → byte4=0x00 (no explicit intake flags)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 1
        car.clim.intake_explicit = False
        data = Msg1D0().encode(car)
        assert data[4] == 0x00

    def test_recirc_bit4_is_recirc_indicator(self):
        """Bit4 of byte4 = recirculation flag (not windshield blowing per earlier autowp docs)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert (data[4] >> 4) & 1 == 1   # bit4 = recirc

    def test_unfrost_front_does_not_set_byte4_bit4(self):
        """Unfrost front is encoded in byte0 (0x19), not in byte4 bit4."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.unfrost_front = 1
        car.clim.intake_explicit = False  # not explicitly set
        data = Msg1D0().encode(car)
        assert (data[4] >> 4) & 1 == 0  # bit4 = recirc; unfrost_front is NOT recirc

    def test_direction_up_left_encodes_in_high_nibble(self):
        """For dir_left=4 ('Up'), byte 3 high nibble = 4; low nibble = dir_right."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 4
        data = Msg1D0().encode(car)
        assert data[3] == 0x40  # (4 << 4) | dir_right=0

    def test_direction_front_left_encodes_in_high_nibble(self):
        """For dir_left=3 ('Front'), byte 3 high nibble = 3; low nibble = dir_right."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 3
        data = Msg1D0().encode(car)
        assert data[3] == 0x30  # (3 << 4) | dir_right=0
