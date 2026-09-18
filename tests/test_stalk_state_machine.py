"""Comprehensive unit test suite for WIP Nav+ steering column controls state machine.

Tests discrete physical button inputs, debounce-free rotary encoder steps,
short vs long press thresholds, concurrent multi-button MUTE triggers, and
CAN 0x21F / 0x221 / 0x3E5 encoding/decoding.
"""

import pytest
from car_state import VirtualCar
from generated import Msg0C5, Msg21F, Msg221, Msg3E5
from stalk_controller import (
    StalkButton,
    StalkEvent,
    StalkEventType,
    StalkStateMachine,
)


class TestStalkStateMachineDiscreteEvents:
    """Test pure state machine transitions and event dispatches."""

    def test_volume_up_short_press(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        # Press down at t=0ms, release at t=150ms (< 1000ms)
        sm.press_down(StalkButton.VOLUME_UP, time_ms=0.0)
        assert sm.can_21f_cmd == StalkStateMachine.CAN_21F_VOL_UP
        assert sm.can_21f_btn_state == StalkStateMachine.STATE_PRESSED

        sm.release(StalkButton.VOLUME_UP, time_ms=150.0)

        event_types = [e.event_type for e in events]
        assert event_types == [
            StalkEventType.PRESS_DOWN,
            StalkEventType.RELEASE,
            StalkEventType.SHORT_PRESS,
        ]
        assert events[-1].payload == "volume_up"
        assert events[-1].duration_ms == 150.0

    def test_volume_down_short_press(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        sm.press_down(StalkButton.VOLUME_DOWN, time_ms=0.0)
        assert sm.can_21f_cmd == StalkStateMachine.CAN_21F_VOL_DOWN
        sm.release(StalkButton.VOLUME_DOWN, time_ms=100.0)

        event_types = [e.event_type for e in events]
        assert event_types == [
            StalkEventType.PRESS_DOWN,
            StalkEventType.RELEASE,
            StalkEventType.SHORT_PRESS,
        ]
        assert events[-1].payload == "volume_down"

    def test_concurrent_volume_up_and_down_triggers_mute(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        # Press VOL_UP, then immediately press VOL_DOWN concurrently
        sm.press_down(StalkButton.VOLUME_UP, time_ms=0.0)
        sm.press_down(StalkButton.VOLUME_DOWN, time_ms=20.0)

        assert sm.can_21f_cmd == StalkStateMachine.CAN_21F_MUTE
        concurrent_events = [e for e in events if e.event_type == StalkEventType.CONCURRENT_PRESS]
        assert len(concurrent_events) == 1
        assert concurrent_events[0].payload == "mute"

        # Release both
        sm.release(StalkButton.VOLUME_UP, time_ms=100.0)
        sm.release(StalkButton.VOLUME_DOWN, time_ms=120.0)

        # Neither short-press volume up nor down should be emitted
        short_presses = [e for e in events if e.event_type == StalkEventType.SHORT_PRESS]
        assert len(short_presses) == 0

    def test_src_button_short_press_cycles_source(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        # Press down at 0ms, held 400ms (< 1000ms)
        sm.press_down(StalkButton.SRC_BUTTON, time_ms=0.0)
        sm.step_time(400.0)
        sm.release(StalkButton.SRC_BUTTON, time_ms=400.0)

        short_presses = [e for e in events if e.event_type == StalkEventType.SHORT_PRESS]
        long_presses = [e for e in events if e.event_type == StalkEventType.LONG_PRESS]
        assert len(short_presses) == 1
        assert len(long_presses) == 0
        assert short_presses[0].payload == "cycle_source"
        assert short_presses[0].duration_ms == 400.0

    def test_src_button_long_press_triggers_call_handling(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        # Press down at 0ms, held past 1000ms threshold
        sm.press_down(StalkButton.SRC_BUTTON, time_ms=0.0)
        sm.step_time(1050.0)

        long_presses = [e for e in events if e.event_type == StalkEventType.LONG_PRESS]
        assert len(long_presses) == 1
        assert long_presses[0].payload == "call_handling"
        assert sm.can_21f_cmd == StalkStateMachine.CAN_21F_TEL_PICKUP
        assert sm.can_21f_btn_state == StalkStateMachine.STATE_LONG_PRESS

        # Release after long press: no short press emitted
        sm.release(StalkButton.SRC_BUTTON, time_ms=1200.0)
        short_presses = [e for e in events if e.event_type == StalkEventType.SHORT_PRESS]
        assert len(short_presses) == 0

    def test_trip_button_short_press_cycles_screen(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        # Press down and release at 300ms (< 2000ms)
        sm.press_down(StalkButton.TRIP_BUTTON, time_ms=0.0)
        assert sm.com_right == 1
        sm.release(StalkButton.TRIP_BUTTON, time_ms=300.0)
        assert sm.com_right == 0

        short_presses = [e for e in events if e.event_type == StalkEventType.SHORT_PRESS]
        assert len(short_presses) == 1
        assert short_presses[0].payload == "cycle_trip_screen"

    def test_trip_button_long_press_resets_trip(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        sm.press_down(StalkButton.TRIP_BUTTON, time_ms=0.0)
        sm.step_time(2100.0)

        long_presses = [e for e in events if e.event_type == StalkEventType.LONG_PRESS]
        assert len(long_presses) == 1
        assert long_presses[0].payload == "trip_reset"

        sm.release(StalkButton.TRIP_BUTTON, time_ms=2200.0)
        short_presses = [e for e in events if e.event_type == StalkEventType.SHORT_PRESS]
        assert len(short_presses) == 0

    def test_voice_nav_repeat_short_press(self):
        sm = StalkStateMachine()
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        sm.press_down(StalkButton.VOICE_NAV_REPEAT, time_ms=0.0)
        assert sm.com_left == 1
        sm.release(StalkButton.VOICE_NAV_REPEAT, time_ms=150.0)
        assert sm.com_left == 0

        short_presses = [e for e in events if e.event_type == StalkEventType.SHORT_PRESS]
        assert len(short_presses) == 1
        assert short_presses[0].payload == "voice_repeat"

    def test_rotary_scroll_encoder_no_debounce_lock(self):
        sm = StalkStateMachine(initial_scroll=0x09)
        events: list[StalkEvent] = []
        sm.add_listener(events.append)

        # Rapid CW scroll by 5 steps
        for _ in range(5):
            sm.rotary_scroll(direction=+1)
        assert sm.scroll_counter == 0x0E
        assert len(events) == 5

        # Rapid CCW scroll by 2 steps
        for _ in range(2):
            sm.rotary_scroll(direction=-1)
        assert sm.scroll_counter == 0x0C
        assert len(events) == 7

        # Modulo roll-over test
        sm.rotary_scroll(direction=-1, ticks=20)
        assert sm.scroll_counter == (0x0C - 20) & 0xFF


class TestVirtualCarStalkIntegration:
    """Test integration between StalkStateMachine and VirtualCar state subsystems."""

    def test_src_short_press_cycles_radio_sources(self):
        car = VirtualCar()
        car.radio.input = 'TUN'

        car.steering_wheel.sm.press_down(StalkButton.SRC_BUTTON, time_ms=0.0)
        car.steering_wheel.sm.release(StalkButton.SRC_BUTTON, time_ms=100.0)
        assert car.radio.input == 'CD'

        car.steering_wheel.sm.press_down(StalkButton.SRC_BUTTON, time_ms=200.0)
        car.steering_wheel.sm.release(StalkButton.SRC_BUTTON, time_ms=300.0)
        assert car.radio.input == 'CDC'

    def test_src_long_press_handles_call(self):
        car = VirtualCar()
        car.radio.panel['tel'] = 0

        car.steering_wheel.sm.press_down(StalkButton.SRC_BUTTON, time_ms=0.0)
        car.steering_wheel.sm.step_time(1100.0)
        assert car.radio.panel['tel'] == 1
        car.steering_wheel.sm.release(StalkButton.SRC_BUTTON, time_ms=1200.0)

    def test_trip_screen_cycle_and_reset(self):
        car = VirtualCar()
        assert car.trip.screen == 0

        # Short press 1: Switch to Trip 1
        car.steering_wheel.sm.press_down(StalkButton.TRIP_BUTTON, time_ms=0.0)
        car.steering_wheel.sm.release(StalkButton.TRIP_BUTTON, time_ms=100.0)
        assert car.trip.screen == 1

        # Modify trip 1 values
        car.trip.hist[0]['dist'] = 350
        car.trip.hist[0]['fuel'] = 6.8

        # Long press on Trip 1: Reset Trip 1
        car.steering_wheel.sm.press_down(StalkButton.TRIP_BUTTON, time_ms=500.0)
        car.steering_wheel.sm.step_time(2100.0)
        assert car.trip.hist[0]['dist'] == 0
        assert car.trip.hist[0]['fuel'] == 0.0
        car.steering_wheel.sm.release(StalkButton.TRIP_BUTTON, time_ms=2700.0)

    def test_concurrent_mute_toggles_radio_volume(self):
        car = VirtualCar()
        car.radio.volume = 18
        car.radio.is_muted = False

        # Concurrent press -> Mute
        car.steering_wheel.sm.press_down(StalkButton.VOLUME_UP, time_ms=0.0)
        car.steering_wheel.sm.press_down(StalkButton.VOLUME_DOWN, time_ms=10.0)
        assert car.radio.is_muted is True
        assert car.radio.volume == 0

        car.steering_wheel.sm.release(StalkButton.VOLUME_UP, time_ms=80.0)
        car.steering_wheel.sm.release(StalkButton.VOLUME_DOWN, time_ms=90.0)

        # Concurrent press again -> Unmute
        car.steering_wheel.sm.press_down(StalkButton.VOLUME_UP, time_ms=200.0)
        car.steering_wheel.sm.press_down(StalkButton.VOLUME_DOWN, time_ms=210.0)
        assert car.radio.is_muted is False
        assert car.radio.volume == 18

    def test_voice_nav_repeat_triggers_trip_voice(self):
        car = VirtualCar()
        initial_repeats = car.trip.voice_repeats
        car.steering_wheel.sm.press_down(StalkButton.VOICE_NAV_REPEAT, time_ms=0.0)
        assert car.trip.voice_repeats == initial_repeats + 1
        assert car.trip.com_left == 1
        car.steering_wheel.sm.release(StalkButton.VOICE_NAV_REPEAT, time_ms=100.0)


class TestCANMessageEncodingWithStalk:
    """Test Msg21F, Msg221, and Msg3E5 CAN frame generation."""

    def test_msg21f_encoding_volume_and_scroll(self):
        car = VirtualCar()
        car.steering_wheel.active = True
        car.steering_wheel.sm.scroll_counter = 0x0B

        # Trigger Seek Up
        car.steering_wheel.sm.press_down(StalkButton.SEEK_UP, time_ms=0.0)
        frame = Msg21F().encode(car)
        assert frame == [0x80, 0x0B, 0x00]

    def test_msg221_trip_stalk_tip(self):
        car = VirtualCar()
        car.trip.press_com('com_right')
        frame = Msg221().encode(car)
        assert frame is not None
        assert (frame[0] & 0x08) != 0  # com_right bit asserted

    def test_steering_wheel_trip_button_sets_com_right_immediately(self):
        car = VirtualCar()
        car.steering_wheel.sm.press_down(StalkButton.TRIP_BUTTON, time_ms=0.0)
        assert car.trip.com_right == 1
        frame = Msg221().encode(car)
        assert (frame[0] & 0x08) != 0  # com_right bit 3 is asserted

        car.steering_wheel.sm.release(StalkButton.TRIP_BUTTON, time_ms=100.0)
        assert car.trip.com_right == 0
        frame_released = Msg221().encode(car)
        assert (frame_released[0] & 0x08) == 0  # com_right bit 3 is cleared

    def test_steering_wheel_voice_nav_repeat_sets_com_left_immediately(self):
        car = VirtualCar()
        car.steering_wheel.sm.press_down(StalkButton.VOICE_NAV_REPEAT, time_ms=0.0)
        assert car.trip.com_left == 1
        frame = Msg221().encode(car)
        assert (frame[0] & 0x01) != 0  # com_left bit 0 is asserted

        car.steering_wheel.sm.release(StalkButton.VOICE_NAV_REPEAT, time_ms=100.0)
        assert car.trip.com_left == 0
        frame_released = Msg221().encode(car)
        assert (frame_released[0] & 0x01) == 0  # com_left bit 0 is cleared

    def test_msg3e5_radio_fascia_buttons_encoding_and_decoding(self):
        car = VirtualCar()
        car.radio.active = True
        car.radio.panel['menu'] = 1
        car.radio.panel['ok'] = 1

        frame = Msg3E5().encode(car)
        assert frame is not None
        assert (frame[0] & 0x40) != 0  # menu is b0 bit 6
        assert (frame[2] & 0x40) != 0  # ok is b2 bit 6

        # Test decode
        new_car = VirtualCar()
        Msg3E5().decode(new_car, frame)
        assert new_car.radio.panel['menu'] == 1
        assert new_car.radio.panel['ok'] == 1

