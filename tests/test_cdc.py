"""CDChanger state and CAN message tests."""

import pytest

from car_state import VirtualCar, CDChanger
from can_messages import ALL_MESSAGES, Msg1A0, Msg131


class TestCDChangerDefaults:
    def test_virtual_car_has_cdc(self):
        car = VirtualCar()
        assert hasattr(car, 'cdc')
        assert isinstance(car.cdc, CDChanger)

    def test_cdc_default_inactive(self):
        car = VirtualCar()
        assert car.cdc.active is False

    def test_cdc_default_status_idle(self):
        car = VirtualCar()
        assert car.cdc.status == CDChanger.STATUS_IDLE

    def test_cdc_default_disc_one(self):
        car = VirtualCar()
        assert car.cdc.disc == 1
        assert car.cdc.track == 1

    def test_cdc_default_time_zero(self):
        car = VirtualCar()
        assert car.cdc.minutes == 0
        assert car.cdc.seconds == 0

    def test_cdc_default_modes_off(self):
        car = VirtualCar()
        assert car.cdc.random is False
        assert car.cdc.repeat is False
        assert car.cdc.repeat_track is False
        assert car.cdc.scan is False

    def test_cdc_status_constants(self):
        assert CDChanger.STATUS_IDLE == 0
        assert CDChanger.STATUS_PLAYING == 1
        assert CDChanger.STATUS_PAUSED == 2
        assert CDChanger.STATUS_LOADING == 3
        assert CDChanger.STATUS_SEARCHING == 4

    def test_cdc_default_disc_tracks(self):
        car = VirtualCar()
        assert hasattr(car.cdc, 'disc_tracks')
        # All 6 discs should default to 10 tracks
        for i in range(1, 7):
            assert car.cdc.disc_tracks[i] == 10

    def test_cdc_total_tracks_property_reflects_current_disc(self):
        car = VirtualCar()
        car.cdc.disc = 1
        car.cdc.disc_tracks[1] = 8
        car.cdc.disc_tracks[3] = 15
        assert car.cdc.total_tracks == 8
        car.cdc.disc = 3
        assert car.cdc.total_tracks == 15

    def test_cdc_total_tracks_setter_targets_current_disc(self):
        car = VirtualCar()
        car.cdc.disc = 2
        car.cdc.total_tracks = 12
        assert car.cdc.disc_tracks[2] == 12
        # Other discs should be unaffected
        assert car.cdc.disc_tracks[1] == 10
        assert car.cdc.disc_tracks[3] == 10

    def test_cdc_total_tracks_independent_per_disc(self):
        car = VirtualCar()
        for i in range(1, 7):
            car.cdc.disc = i
            car.cdc.total_tracks = i * 3
        for i in range(1, 7):
            car.cdc.disc = i
            assert car.cdc.total_tracks == i * 3


class TestMsg1A0Encode:
    def test_returns_none_when_cdc_inactive(self):
        car = VirtualCar()
        assert car.cdc.active is False
        assert Msg1A0().encode(car) is None

    def test_idle_status_encodes_no_magazine_byte(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_IDLE
        data = Msg1A0().encode(car)
        assert data is not None
        assert data[0] == 0x80

    def test_playing_status_encodes_play_byte(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_PLAYING
        data = Msg1A0().encode(car)
        assert data[0] == 0x04

    def test_paused_status_encodes_pause_byte(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_PAUSED
        data = Msg1A0().encode(car)
        assert data[0] == 0x02

    def test_loading_status_encodes_loading_byte(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_LOADING
        data = Msg1A0().encode(car)
        assert data[0] == 0x01

    def test_searching_status_encodes_searching_byte(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_SEARCHING
        data = Msg1A0().encode(car)
        assert data[0] == 0x40

    def test_disc_and_track_in_correct_bytes(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.disc = 3
        car.cdc.track = 7
        data = Msg1A0().encode(car)
        assert data[1] == 3
        assert data[2] == 7

    def test_track_time_in_correct_bytes(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_PLAYING
        car.cdc.minutes = 4
        car.cdc.seconds = 35
        data = Msg1A0().encode(car)
        assert data[3] == 4
        assert data[4] == 35

    def test_total_tracks_in_byte5(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.total_tracks = 12
        data = Msg1A0().encode(car)
        assert data[5] == 12

    def test_random_mode_flag(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.random = True
        data = Msg1A0().encode(car)
        assert data[6] & 0x02

    def test_repeat_mode_flag(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.repeat = True
        data = Msg1A0().encode(car)
        assert data[6] & 0x04

    def test_scan_mode_flag(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.scan = True
        data = Msg1A0().encode(car)
        assert data[6] & 0x01

    def test_repeat_track_flag(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.repeat_track = True
        data = Msg1A0().encode(car)
        assert data[6] & 0x08

    def test_byte7_always_zero(self):
        car = VirtualCar()
        car.cdc.active = True
        data = Msg1A0().encode(car)
        assert data[7] == 0x00

    def test_no_modes_set_byte6_zero(self):
        car = VirtualCar()
        car.cdc.active = True
        data = Msg1A0().encode(car)
        assert data[6] == 0x00

    def test_required_modules_contains_cdc(self):
        assert 'cdc' in Msg1A0.required_modules


class TestMsg1A0Decode:
    def test_decode_playing_status(self):
        car = VirtualCar()
        Msg1A0().decode(car, [0x04, 2, 5, 1, 30, 8, 0x00, 0x00])
        assert car.cdc.status == CDChanger.STATUS_PLAYING
        assert car.cdc.disc == 2
        assert car.cdc.track == 5
        assert car.cdc.minutes == 1
        assert car.cdc.seconds == 30
        assert car.cdc.total_tracks == 8

    def test_decode_paused_status(self):
        car = VirtualCar()
        Msg1A0().decode(car, [0x02, 1, 3, 0, 0, 10, 0x00, 0x00])
        assert car.cdc.status == CDChanger.STATUS_PAUSED

    def test_decode_loading_status(self):
        car = VirtualCar()
        Msg1A0().decode(car, [0x01, 1, 1, 0, 0, 0, 0x00, 0x00])
        assert car.cdc.status == CDChanger.STATUS_LOADING

    def test_decode_searching_status(self):
        car = VirtualCar()
        Msg1A0().decode(car, [0x40, 3, 1, 0, 0, 0, 0x00, 0x00])
        assert car.cdc.status == CDChanger.STATUS_SEARCHING

    def test_decode_idle_status(self):
        car = VirtualCar()
        Msg1A0().decode(car, [0x80, 0, 0, 0, 0, 0, 0x00, 0x00])
        assert car.cdc.status == CDChanger.STATUS_IDLE

    def test_decode_mode_flags(self):
        car = VirtualCar()
        # random=0x02, repeat=0x04, scan=0x01, repeat_track=0x08
        Msg1A0().decode(car, [0x04, 1, 1, 0, 0, 10, 0x0F, 0x00])
        assert car.cdc.scan is True
        assert car.cdc.random is True
        assert car.cdc.repeat is True
        assert car.cdc.repeat_track is True

    def test_decode_no_mode_flags(self):
        car = VirtualCar()
        Msg1A0().decode(car, [0x04, 1, 1, 0, 0, 10, 0x00, 0x00])
        assert car.cdc.scan is False
        assert car.cdc.random is False
        assert car.cdc.repeat is False
        assert car.cdc.repeat_track is False

    def test_decode_too_short_is_noop(self):
        car = VirtualCar()
        original_disc = car.cdc.disc
        Msg1A0().decode(car, [0x04, 2])  # only 2 bytes
        assert car.cdc.disc == original_disc


class TestMsg1A0Roundtrip:
    def test_encode_decode_roundtrip(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_PLAYING
        car.cdc.disc = 4
        car.cdc.track = 9
        car.cdc.minutes = 3
        car.cdc.seconds = 47
        car.cdc.total_tracks = 15
        car.cdc.random = True
        car.cdc.repeat = False
        data = Msg1A0().encode(car)
        car2 = VirtualCar()
        Msg1A0().decode(car2, data)
        assert car2.cdc.status == CDChanger.STATUS_PLAYING
        assert car2.cdc.disc == 4
        assert car2.cdc.track == 9
        assert car2.cdc.minutes == 3
        assert car2.cdc.seconds == 47
        assert car2.cdc.total_tracks == 15
        assert car2.cdc.random is True
        assert car2.cdc.repeat is False


class TestMsg131Encode:
    def test_encode_always_returns_none(self):
        """CDC does not transmit 0x131 — radio does."""
        car = VirtualCar()
        assert Msg131().encode(car) is None

    def test_required_modules_contains_cdc(self):
        assert 'cdc' in Msg131.required_modules


class TestMsg131Decode:
    def test_cdc_selected_and_play_request_sets_playing(self):
        car = VirtualCar()
        car.cdc.active = True
        # 0x90 = bit7 (CDC selected) + bit4 (play)
        Msg131().decode(car, [0x90, 0])
        assert car.cdc.status == CDChanger.STATUS_PLAYING

    def test_cdc_selected_without_play_sets_paused(self):
        car = VirtualCar()
        car.cdc.active = True
        # 0x80 = bit7 (CDC selected), no bit4 (no play)
        Msg131().decode(car, [0x80, 0])
        assert car.cdc.status == CDChanger.STATUS_PAUSED

    def test_cdc_deselected_sets_idle(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.status = CDChanger.STATUS_PLAYING
        # 0x00 = CDC not selected
        Msg131().decode(car, [0x00, 0])
        assert car.cdc.status == CDChanger.STATUS_IDLE

    def test_disc_change_triggers_searching(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.disc = 1
        # 0x82 = CDC selected (0x80) + disc 2 (0x02)
        Msg131().decode(car, [0x82, 0])
        assert car.cdc.disc == 2
        assert car.cdc.status == CDChanger.STATUS_SEARCHING
        assert car.cdc.track == 1
        assert car.cdc.minutes == 0
        assert car.cdc.seconds == 0

    def test_same_disc_no_searching(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.disc = 2
        car.cdc.status = CDChanger.STATUS_PLAYING
        # 0x92 = CDC selected (0x80) + play (0x10) + disc 2 (0x02)
        Msg131().decode(car, [0x92, 0])
        # Same disc, no searching — stays playing
        assert car.cdc.disc == 2
        assert car.cdc.status == CDChanger.STATUS_PLAYING

    def test_track_change_resets_time(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.track = 1
        car.cdc.minutes = 5
        car.cdc.seconds = 30
        # 0x90 = CDC selected + play; track_req = 5
        Msg131().decode(car, [0x90, 5])
        assert car.cdc.track == 5
        assert car.cdc.minutes == 0
        assert car.cdc.seconds == 0

    def test_same_track_no_time_reset(self):
        car = VirtualCar()
        car.cdc.active = True
        car.cdc.track = 3
        car.cdc.minutes = 2
        car.cdc.seconds = 15
        # track_req = 3 (same) — time should be unchanged
        Msg131().decode(car, [0x90, 3])
        assert car.cdc.minutes == 2
        assert car.cdc.seconds == 15

    def test_noop_when_cdc_not_active(self):
        car = VirtualCar()
        car.cdc.active = False
        car.cdc.status = CDChanger.STATUS_IDLE
        Msg131().decode(car, [0x90, 1])
        assert car.cdc.status == CDChanger.STATUS_IDLE

    def test_too_short_frame_is_noop(self):
        car = VirtualCar()
        car.cdc.active = True
        original_status = car.cdc.status
        Msg131().decode(car, [0x90])  # only 1 byte
        assert car.cdc.status == original_status


class TestMsg1A0InAllMessages:
    def test_1a0_in_all_messages(self):
        assert 0x1A0 in ALL_MESSAGES
        assert ALL_MESSAGES[0x1A0] is Msg1A0

    def test_131_in_all_messages(self):
        assert 0x131 in ALL_MESSAGES
        assert ALL_MESSAGES[0x131] is Msg131

