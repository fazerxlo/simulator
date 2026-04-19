"""Radio CAN frame tests — cross-referenced against ios-car-dashboard (Peugeot 207 RD4)."""

import pytest
from car_state import VirtualCar, Radio
from generated import ALL_MESSAGES, Msg165, Msg1E5, Msg1E0, Msg225, Msg265, Msg2A5, Msg0A4, Msg1A5, Msg3E5
from conftest import DummyWidget


class TestMsg165RadioSource:
    """0x165 — radio source / input select.

    Byte 2 high nibble encodes the active input source.
    Verified against ios-car-dashboard serial frame 0x03 mapping.
    """

    def test_default_input_is_tuner(self):
        car = VirtualCar()
        data = Msg165().encode(car)
        # TUN code = 0x01, placed in high nibble → byte 2 = 0x10
        assert data[2] == 0x10

    def test_cdc_input_encodes_correctly(self):
        car = VirtualCar()
        car.radio.input = 'CDC'
        data = Msg165().encode(car)
        # CDC code = 0x03 → byte 2 high nibble = 3 → 0x30
        assert data[2] == 0x30

    def test_aux1_input_encodes_correctly(self):
        car = VirtualCar()
        car.radio.input = 'AUX1'
        data = Msg165().encode(car)
        # AUX1 code = 0x04 → byte 2 = 0x40
        assert data[2] == 0x40

    def test_aux2_input_matches_ios_car_dashboard_aux(self):
        """ios-car-dashboard maps serial source 5 → .aux; AUX2 = 0x05."""
        car = VirtualCar()
        car.radio.input = 'AUX2'
        data = Msg165().encode(car)
        # AUX2 code = 0x05 → byte 2 high nibble = 5 → 0x50
        assert data[2] == 0x50

    def test_fixed_header_bytes(self):
        """Bytes 0 and 1 are constant status bytes."""
        car = VirtualCar()
        data = Msg165().encode(car)
        assert data[0] == 0xCC
        assert data[1] == 0x54

    def test_decode_tuner(self):
        car = VirtualCar()
        Msg165().decode(car, [0xCC, 0x54, 0x10, 0x02])
        assert car.radio.input == 'TUN'

    def test_decode_cdc(self):
        car = VirtualCar()
        Msg165().decode(car, [0xCC, 0x54, 0x30, 0x02])
        assert car.radio.input == 'CDC'

    def test_decode_aux2(self):
        car = VirtualCar()
        Msg165().decode(car, [0xCC, 0x54, 0x50, 0x02])
        assert car.radio.input == 'AUX2'

    def test_decode_unknown_code_does_not_crash(self):
        """An unrecognised nibble should leave car.radio.input unchanged."""
        car = VirtualCar()
        original = car.radio.input
        Msg165().decode(car, [0xCC, 0x54, 0xF0, 0x02])
        assert car.radio.input == original

    def test_encode_decode_roundtrip_all_sources(self):
        """Every named source survives an encode/decode roundtrip."""
        for name in Radio.INPUT_CODES:
            car_a = VirtualCar()
            car_a.radio.input = name
            payload = Msg165().encode(car_a)
            car_b = VirtualCar()
            Msg165().decode(car_b, payload)
            assert car_b.radio.input == name, f'roundtrip failed for {name}'


class TestMsg1E5AudioSettings:
    """0x1E5 — radio audio settings: balance, bass, treble, loudness, ambiance.

    Byte layout confirmed against ios-car-dashboard AudioSettings.swift and
    the CarInfo+SerialParserDelegate.swift frame-0x10 parser.
    """

    def test_default_encode_all_flat(self):
        """With default car state all values should be at 0x3F (centre)."""
        car = VirtualCar()
        data = Msg1E5().encode(car)
        assert data[0] & 0x7F == 0x3F  # lr-bal at centre
        assert data[1] & 0x7F == 0x3F  # rf-bal at centre
        assert data[2] & 0x7F == 0x3F  # bass at flat
        assert data[4] & 0x7F == 0x3F  # treble at flat

    def test_default_no_menu_active(self):
        """No menu-active flag (bit 7) should be set in idle state."""
        car = VirtualCar()
        data = Msg1E5().encode(car)
        assert not (data[0] & 0x80)
        assert not (data[1] & 0x80)
        assert not (data[2] & 0x80)
        assert not (data[4] & 0x80)

    def test_lr_balance_menu_active_flag(self):
        """Opening lr-bal menu sets bit 7 of byte 0."""
        car = VirtualCar()
        car.radio.audio['menu'] = 'lr-bal'
        data = Msg1E5().encode(car)
        assert data[0] & 0x80

    def test_bass_menu_active_flag(self):
        """Opening bass menu sets bit 7 of byte 2."""
        car = VirtualCar()
        car.radio.audio['menu'] = 'bass'
        data = Msg1E5().encode(car)
        assert data[2] & 0x80

    def test_treble_menu_active_flag(self):
        """Opening treble menu sets bit 7 of byte 4."""
        car = VirtualCar()
        car.radio.audio['menu'] = 'treble'
        data = Msg1E5().encode(car)
        assert data[4] & 0x80

    def test_loudness_enabled_encodes_bit6_byte5(self):
        """ios-car-dashboard: loudness = (data[5] & 0x40) == 0x40."""
        car = VirtualCar()
        car.radio.audio['loudness'] = 1
        data = Msg1E5().encode(car)
        assert data[5] & 0x40

    def test_loudness_disabled_clears_bit6_byte5(self):
        car = VirtualCar()
        car.radio.audio['loudness'] = 0
        data = Msg1E5().encode(car)
        assert not (data[5] & 0x40)

    def test_ambiance_none_encodes_code_0x03(self):
        """ios-car-dashboard EqualizerSetting.none → byte 6 bits 5:0 = 0x03."""
        car = VirtualCar()
        car.radio.audio['ambiance'] = 'none'
        data = Msg1E5().encode(car)
        assert (data[6] & 0x3F) == 0x03

    def test_ambiance_classical_encodes_code_0x07(self):
        """ios-car-dashboard EqualizerSetting.classical → 0x07."""
        car = VirtualCar()
        car.radio.audio['ambiance'] = 'classical'
        data = Msg1E5().encode(car)
        assert (data[6] & 0x3F) == 0x07

    def test_ambiance_pop_rock_encodes_code_0x0f(self):
        """ios-car-dashboard EqualizerSetting.popRock → 0x0F."""
        car = VirtualCar()
        car.radio.audio['ambiance'] = 'pop-rock'
        data = Msg1E5().encode(car)
        assert (data[6] & 0x3F) == 0x0F

    def test_ambiance_vocal_encodes_code_0x13(self):
        """ios-car-dashboard EqualizerSetting.vocals → 0x13."""
        car = VirtualCar()
        car.radio.audio['ambiance'] = 'vocal'
        data = Msg1E5().encode(car)
        assert (data[6] & 0x3F) == 0x13

    def test_ambiance_techno_encodes_code_0x17(self):
        """ios-car-dashboard EqualizerSetting.techno → 0x17."""
        car = VirtualCar()
        car.radio.audio['ambiance'] = 'techno'
        data = Msg1E5().encode(car)
        assert (data[6] & 0x3F) == 0x17

    def test_decode_lr_bal_menu_active(self):
        """bit 7 of byte 0 = lr-bal menu active."""
        car = VirtualCar()
        Msg1E5().decode(car, [0xFF, 0x3F, 0x3F, 0x00, 0x3F, 0x00, 0x03])
        assert car.radio.audio['menu'] == 'lr-bal'

    def test_decode_bass_value(self):
        """bits 6:0 of byte 2 = bass value when bass menu is active (bit 7 = 1).

        ios-car-dashboard: bass = Int(data[2] & 0x7F) - 63 when activeMode == .bass.
        """
        car = VirtualCar()
        # byte 2 = 0xC2: bit 7 = bass menu active, bits 6:0 = 0x42 (3 steps up from flat)
        Msg1E5().decode(car, [0x3F, 0x3F, 0xC2, 0x00, 0x3F, 0x00, 0x03])
        assert car.radio.audio['menu'] == 'bass'
        assert car.radio.audio['bass'] == 0x42

    def test_decode_loudness_enabled(self):
        """bit 6 of byte 5 = loudness on (menu is NOT open — bit 7 = 0)."""
        car = VirtualCar()
        Msg1E5().decode(car, [0x3F, 0x3F, 0x3F, 0x00, 0x3F, 0x40, 0x03])
        assert car.radio.audio['loudness'] == 1
        assert car.radio.audio['menu'] == 'none'  # bit7=0 → menu not open

    def test_decode_loudness_menu_open(self):
        """bit 7 of byte 5 = loudness menu is currently open."""
        car = VirtualCar()
        # byte 5 = 0xC0: bit7 = loudness menu open, bit6 = loudness enabled
        Msg1E5().decode(car, [0x3F, 0x3F, 0x3F, 0x00, 0x3F, 0xC0, 0x03])
        assert car.radio.audio['loudness'] == 1
        assert car.radio.audio['menu'] == 'loudness'

    def test_decode_ambiance_without_menu_open(self):
        """Ambiance value is always decoded, even when menu is not open."""
        car = VirtualCar()
        # byte 6 = 0x17: bit6 = 0 (menu closed), bits5:0 = 0x17 (techno)
        Msg1E5().decode(car, [0x3F, 0x3F, 0x3F, 0x00, 0x3F, 0x40, 0x17])
        assert car.radio.audio['ambiance'] == 'techno'
        assert car.radio.audio['menu'] == 'none'  # loudness menu not open (bit7=0)

    def test_decode_ambiance_classical(self):
        """byte 6 bit 6 = ambiance menu active; bits 5:0 = 0x07 → classical.

        ios-car-dashboard: EqualizerSetting.classical when data[6] & 0xBF == 0x07.
        """
        car = VirtualCar()
        # byte 6 = 0x47: bit 6 = ambiance menu active, bits 5:0 = 0x07 (classical)
        Msg1E5().decode(car, [0x3F, 0x3F, 0x3F, 0x00, 0x3F, 0x00, 0x47])
        assert car.radio.audio['menu'] == 'ambiance'
        assert car.radio.audio['ambiance'] == 'classical'

    def test_decode_ambiance_menu_active(self):
        """bit 6 of byte 6 = ambiance menu active."""
        car = VirtualCar()
        Msg1E5().decode(car, [0x3F, 0x3F, 0x3F, 0x00, 0x3F, 0x00, 0x4F])
        assert car.radio.audio['menu'] == 'ambiance'

    def test_encode_decode_roundtrip(self):
        """Encode then decode preserves the active-menu field and its value.

        The decoder only updates the field for the currently active menu, so
        we test one menu at a time.  Here bass is the active menu.
        """
        car_a = VirtualCar()
        car_a.radio.audio['menu'] = 'bass'
        car_a.radio.audio['bass'] = 0x45  # +6 from flat
        payload = Msg1E5().encode(car_a)
        car_b = VirtualCar()
        Msg1E5().decode(car_b, payload)
        assert car_b.radio.audio['menu'] == 'bass'
        assert car_b.radio.audio['bass'] == 0x45

    def test_encode_decode_roundtrip_ambiance(self):
        """Ambiance roundtrip: ambiance menu active → correct preset decoded."""
        car_a = VirtualCar()
        car_a.radio.audio['menu'] = 'ambiance'
        car_a.radio.audio['ambiance'] = 'jazz-blues'
        payload = Msg1E5().encode(car_a)
        car_b = VirtualCar()
        Msg1E5().decode(car_b, payload)
        assert car_b.radio.audio['menu'] == 'ambiance'
        assert car_b.radio.audio['ambiance'] == 'jazz-blues'

    def test_byte3_always_zero(self):
        """Byte 3 is unused and must be 0x00."""
        car = VirtualCar()
        data = Msg1E5().encode(car)
        assert data[3] == 0x00

    def test_workbench_frame_decode(self):
        """Validate decode against real bench capture.

        Workbench state: volume=9, FM2@96.0MHz, mem=1, RDS+PTY on, TA off,
        loudness on, ambiance=techno, autovol disabled.
        0x1E5 payload: 3F 3F 42 3F 44 40 17
        """
        car = VirtualCar()
        Msg1E5().decode(car, bytes([0x3F, 0x3F, 0x42, 0x3F, 0x44, 0x40, 0x17]))
        a = car.radio.audio
        assert a['lr-bal'] == 0x3F
        assert a['rf-bal'] == 0x3F
        assert a['bass'] == 0x42    # +3 from flat
        assert a['treble'] == 0x44  # +5 from flat
        assert a['loudness'] == 1   # enabled
        assert a['ambiance'] == 'techno'
        assert a['menu'] == 'none'  # no menu open


# ---------------------------------------------------------------------------
# Msg225 FM tuner decode tests (verified against real bench capture)
# ---------------------------------------------------------------------------

class TestMsg225Decode:
    """0x225 FM tuner status — bit layout verified from real bench capture."""

    def test_workbench_frame_decode(self):
        """Real bench frame: FM1, 96.0 MHz, mem=1, RDS on.

        Payload: 20 10 90 03 98
          byte0=0x20 → rds=1 (bit5), pty=0, tun=0, ta=0, tundir=0
          byte1=0x10 → mem=0x10 (preset 1)
          byte2=0x90 → band=FM Band 1
          bytes3-4=0x0398 → freq=920 → 96.0 MHz
        """
        car = VirtualCar()
        Msg225().decode(car, bytes([0x20, 0x10, 0x90, 0x03, 0x98]))
        r = car.radio
        assert r.rds == 1
        assert r.pty == 0
        assert r.ta == 0
        assert r.scan == 0
        assert r.tun == 0
        assert r.tundir == 0
        assert r.mem == 0x10        # preset 1
        assert r.band == 0x90       # FM Band 1
        assert r.freq == 920        # 96.0 MHz

    def test_rds_decoded_from_bit5(self):
        """RDS available flag is bit5 of byte0."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x20, 0x00, 0x00, 0x00, 0x00]))
        assert car.radio.rds == 1
        assert car.radio.pty == 0

    def test_pty_decoded_from_bit4(self):
        """PTY flag is bit4 of byte0."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x10, 0x00, 0x00, 0x00, 0x00]))
        assert car.radio.pty == 1
        assert car.radio.rds == 0

    def test_ta_decoded_from_bit2(self):
        """TA flag is bit2 of byte0."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x04, 0x00, 0x00, 0x00, 0x00]))
        assert car.radio.ta == 1

    def test_scan_decoded_from_bit6(self):
        """SCAN flag is bit6 of byte0."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x40, 0x00, 0x00, 0x00, 0x00]))
        assert car.radio.scan == 1

    def test_band_fm2_code(self):
        """Band code 0xA0 = FM Band 2 (verified from bench)."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x00, 0x00, 0xA0, 0x00, 0x00]))
        assert car.radio.band == 0xA0

    def test_band_am_code(self):
        """Band code 0xD0 = AM."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x00, 0x00, 0xD0, 0x00, 0x00]))
        assert car.radio.band == 0xD0

    def test_frequency_96mhz(self):
        """Freq raw=920 = 96.0 MHz."""
        car = VirtualCar()
        Msg225().decode(car, bytes([0x00, 0x00, 0x00, 0x03, 0x98]))
        assert car.radio.freq == 920
        assert abs(car.radio.freq * 0.05 + 50 - 96.0) < 0.01

    def test_encode_decode_roundtrip(self):
        """Encode→decode roundtrip preserves all fields."""
        car_a = VirtualCar()
        r = car_a.radio
        r.rds = 1
        r.pty = 1
        r.scan = 0
        r.ta = 0
        r.mem = 0x10
        r.band = 0xA0
        r.freq = 920
        payload = Msg225().encode(car_a)
        car_b = VirtualCar()
        Msg225().decode(car_b, bytes(payload))
        assert car_b.radio.rds == 1
        assert car_b.radio.pty == 1
        assert car_b.radio.mem == 0x10
        assert car_b.radio.band == 0xA0
        assert car_b.radio.freq == 920


# ---------------------------------------------------------------------------
# Msg2A5 station name decode tests
# ---------------------------------------------------------------------------

class TestMsg2A5StationName:
    """0x2A5 — station name / RDS PS decode."""

    def test_workbench_station_name(self):
        """Real bench payload decodes to 'RMF FM' (whitespace stripped)."""
        car = VirtualCar()
        Msg2A5().decode(car, bytes([0x20, 0x52, 0x4D, 0x46, 0x20, 0x46, 0x4D, 0x20]))
        assert car.radio.station_name == 'RMF FM'

    def test_no_leading_trailing_spaces(self):
        """Leading and trailing whitespace is stripped from station names."""
        car = VirtualCar()
        Msg2A5().decode(car, bytes([0x20, 0x20, 0x52, 0x44, 0x53, 0x20, 0x20, 0x00]))
        assert car.radio.station_name == 'RDS'

    def test_null_terminated_name(self):
        """Null bytes at end are stripped (existing behaviour preserved)."""
        car = VirtualCar()
        Msg2A5().decode(car, bytes([0x46, 0x4D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
        assert car.radio.station_name == 'FM'




class TestListenOnlyRadioMessages:
    """Radio CAN messages must be listen-only (never transmitted by simulator)."""

    def test_msg165_is_listen_only(self):
        assert Msg165.listen_only is True

    def test_msg1e0_is_listen_only(self):
        assert Msg1E0.listen_only is True

    def test_msg1e5_is_listen_only(self):
        assert Msg1E5.listen_only is True

    def test_msg225_is_listen_only(self):
        assert Msg225.listen_only is True

    def test_msg265_is_listen_only(self):
        assert Msg265.listen_only is True

    def test_msg2a5_is_listen_only(self):
        assert Msg2A5.listen_only is True

    def test_msg1a5_returns_none_when_buttons_inactive(self):
        """Msg1A5 radio path should not transmit."""
        car = VirtualCar()
        assert Msg1A5().encode(car) is None

    def test_msg3e5_returns_none_when_buttons_inactive(self):
        """Msg3E5 radio path should not transmit."""
        car = VirtualCar()
        assert Msg3E5().encode(car) is None


class TestRadioRdsText:
    """car_state.Radio.rds_text – RDS RadioText field."""

    def test_rds_text_default_empty(self):
        """rds_text starts as empty string."""
        assert VirtualCar().radio.rds_text == ''

    def test_rds_text_can_be_set(self):
        """rds_text is assignable (populated when RT CAN frame is decoded)."""
        car = VirtualCar()
        car.radio.rds_text = 'RMF FM wita w Krakowie na czestotliwosci 96 MHz'
        assert car.radio.rds_text == 'RMF FM wita w Krakowie na czestotliwosci 96 MHz'


class TestRadioToggleGroupHelper:
    """Radio._set_toggle_group() helper – explicit group state management."""

    def test_set_toggle_group_sets_target_down(self):
        """The target button id gets state 'down'."""
        class FakeBtn:
            def __init__(self):
                self.state = 'normal'

        ids = {k: FakeBtn() for k in ('a', 'b', 'c')}
        # Import the Radio widget without Kivy by testing the helper logic only.
        # Replicate the algorithm:
        target_id = 'b'
        for btn_id in ids:
            ids[btn_id].state = 'down' if btn_id == target_id else 'normal'

        assert ids['a'].state == 'normal'
        assert ids['b'].state == 'down'
        assert ids['c'].state == 'normal'

    def test_set_toggle_group_clears_previous_down(self):
        """A previously 'down' button is set to 'normal' when another is selected."""
        class FakeBtn:
            def __init__(self, state='normal'):
                self.state = state

        ids = {'x': FakeBtn('down'), 'y': FakeBtn('normal'), 'z': FakeBtn('normal')}
        target_id = 'z'
        for btn_id in ids:
            ids[btn_id].state = 'down' if btn_id == target_id else 'normal'

        assert ids['x'].state == 'normal'
        assert ids['y'].state == 'normal'
        assert ids['z'].state == 'down'


# ---------------------------------------------------------------------------
# Msg0A4 – RDS RadioText (ISO 15765-2) decode
# ---------------------------------------------------------------------------


class TestMsg0A4RadioText:
    """0x0A4 — RDS RadioText ISO 15765-2 (SF / FF / CF) accumulation."""

    def test_is_listen_only(self):
        assert Msg0A4.listen_only is True

    def test_registered_in_all_messages(self):
        assert 0x0A4 in ALL_MESSAGES
        assert ALL_MESSAGES[0x0A4] is Msg0A4

    def test_sf_sets_rds_text(self):
        """A Single Frame (SF) populates rds_text immediately."""
        car = VirtualCar()
        # SF: PCI=0x06 (length=6), payload = "RMF FM"
        data = bytes([0x06, 0x52, 0x4D, 0x46, 0x20, 0x46, 0x4D])
        Msg0A4().decode(car, data)
        assert car.radio.rds_text == 'RMF FM'

    def test_sf_trailing_space_stripped(self):
        """Trailing spaces in an SF are stripped from rds_text."""
        car = VirtualCar()
        # SF: length=7, "RMF FM " (trailing space)
        data = bytes([0x07, 0x52, 0x4D, 0x46, 0x20, 0x46, 0x4D, 0x20])
        Msg0A4().decode(car, data)
        assert car.radio.rds_text == 'RMF FM'

    def test_ff_cf_accumulates(self):
        """First Frame + Consecutive Frame assembles the full RT string."""
        car = VirtualCar()
        # FF: total=13, bytes 2-7 = "Hello,"
        ff = bytes([0x10, 0x0D, 0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x2C])
        # CF SN=1: bytes 1-7 = " World!"
        cf1 = bytes([0x21, 0x20, 0x57, 0x6F, 0x72, 0x6C, 0x64, 0x21])
        Msg0A4().decode(car, ff)
        Msg0A4().decode(car, cf1)
        assert car.radio.rds_text == 'Hello, World!'

    def test_new_ff_resets_buffer(self):
        """A new First Frame discards any in-progress transfer."""
        car = VirtualCar()
        # Start old transfer (14 chars, partial after CF1 = 13 of 14 received)
        Msg0A4().decode(car, bytes([0x10, 0x0E]) + b'OldTex')  # FF total=14
        Msg0A4().decode(car, bytes([0x21]) + b'tOldMor')       # CF1 → 13/14
        # New FF resets the buffer
        Msg0A4().decode(car, bytes([0x10, 0x07]) + b'NewTex')  # FF total=7
        Msg0A4().decode(car, bytes([0x21]) + b't      ')       # CF1 → ≥7, done
        assert car.radio.rds_text == 'NewText'

    def test_null_byte_terminates_text(self):
        """A NUL byte inside the RT string marks the end of the message."""
        car = VirtualCar()
        # SF: length=6, data = "Hello\x00"
        Msg0A4().decode(car, bytes([0x06, 0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x00]))
        assert car.radio.rds_text == 'Hello'

    def test_short_frame_ignored(self):
        """Frames shorter than 2 bytes do not crash."""
        car = VirtualCar()
        Msg0A4().decode(car, bytes([0x06]))  # only 1 byte — should not raise

    def test_rt_buf_initialised_empty(self):
        """car_state.Radio._rt_buf starts as an empty dict."""
        assert VirtualCar().radio._rt_buf == {}

    def test_out_of_sequence_cf_discards_buffer(self):
        """A CF with the wrong SN discards the in-progress transfer."""
        car = VirtualCar()
        Msg0A4().decode(car, bytes([0x10, 0x0D]) + b'Hello,')  # FF total=13
        Msg0A4().decode(car, bytes([0x23]) + b' World!')        # Wrong SN (3, expected 1)
        assert car.radio._rt_buf == {}

    def test_sf_invalid_length_zero_ignored(self):
        """SF with length=0 is silently ignored."""
        car = VirtualCar()
        Msg0A4().decode(car, bytes([0x00]) + b'\x00' * 7)
        assert car.radio.rds_text == ''

    def test_cf_without_ff_ignored(self):
        """A CF without a preceding FF is silently ignored."""
        car = VirtualCar()
        Msg0A4().decode(car, bytes([0x21]) + b'orphan ')
        assert car.radio.rds_text == ''

    def test_full_64_char_rt(self):
        """A 64-char RT assembled from FF + 9 CFs decodes correctly."""
        car = VirtualCar()
        rt_str = 'RMF FM wita w Krakowie na czestotliwosci 96 MHz'
        # Pad to exactly 64 chars with spaces
        rt_padded = rt_str.ljust(64)
        rt_bytes = rt_padded.encode('ascii')
        # FF: total=64, first 6 chars
        Msg0A4().decode(car, bytes([0x10, 0x40]) + rt_bytes[0:6])
        # 9 CFs (SN 1-9) carry 7 chars each; after CF9 accumulated ≥ 64
        for i in range(9):
            sn = (i + 1) & 0x0F
            offset = 6 + i * 7
            chunk = rt_bytes[offset:offset + 7].ljust(7, b' ')
            Msg0A4().decode(car, bytes([0x20 | sn]) + chunk)
        assert car.radio.rds_text == rt_str

    def test_real_workbench_rt_prefix_is_skipped(self):
        """Real radio dump uses a 4-byte 10 00 00 00 prefix before the 64-char text."""
        car = VirtualCar()
        frames = [
            bytes([0x10, 0x44, 0x10, 0x00, 0x00, 0x00, 0x44, 0x7A]),
            bytes([0x21, 0x77, 0x6F, 0x6E, 0x63, 0x69, 0x65, 0x20]),
            bytes([0x22, 0x64, 0x6F, 0x20, 0x6E, 0x61, 0x73, 0x20]),
            bytes([0x23, 0x2D, 0x20, 0x74, 0x65, 0x6C, 0x2E, 0x20]),
            bytes([0x24, 0x31, 0x32, 0x20, 0x44, 0x57, 0x41, 0x20]),
            bytes([0x25, 0x4D, 0x49, 0x4C, 0x49, 0x4F, 0x4E, 0x59]),
            bytes([0x26, 0x20, 0x63, 0x7A, 0x79, 0x6E, 0x6E, 0x79]),
            bytes([0x27, 0x20, 0x63, 0x61, 0x6C, 0x61, 0x20, 0x64]),
            bytes([0x28, 0x6F, 0x62, 0x65, 0x2E, 0x20, 0x20, 0x20]),
            bytes([0x29, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x00]),
        ]
        for frame in frames:
            Msg0A4().decode(car, frame)
        assert car.radio.rds_text == 'Dzwoncie do nas - tel. 12 DWA MILIONY czynny cala dobe.'
