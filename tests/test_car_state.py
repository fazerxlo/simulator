"""Tests for car_state.VirtualCar defaults, mutation, and isolation."""
import pytest

from car_state import (BSI, Buttons, Clim, Dashboard, Doors, MFDPopup,
                       Parktronic, Tyres, VirtualCar, Radio, Trip,
                       KMLState, BTEState, SpeedControl)


class TestVirtualCarDefaults:
    def test_bsi_defaults(self):
        car = VirtualCar()
        assert car.bsi.ignition_on is False
        assert car.bsi.power_mode == 0x02
        assert car.bsi.reverse == 0
        assert car.bsi.rpm == 0
        assert car.bsi.speed == 0

    def test_doors_defaults(self):
        car = VirtualCar()
        for attr in ('front_left', 'front_right', 'rear_left', 'rear_right',
                     'boot', 'bonnet', 'rear_window', 'fuel_flap'):
            assert getattr(car.doors, attr) == 0
        assert car.doors.display_active is False

    def test_tyres_defaults(self):
        car = VirtualCar()
        for attr in ('fl', 'fr', 'rl', 'rr'):
            assert getattr(car.tyres, attr) == Tyres.OK
        assert car.tyres.display_active is False
        assert car.tyres.alert_0x168_b1 == 0

    def test_parktronic_defaults(self):
        car = VirtualCar()
        for attr in ('rear_left', 'rear_center', 'rear_right',
                     'front_left', 'front_center', 'front_right'):
            assert getattr(car.parktronic, attr) == 7
        assert car.parktronic.display == 0

    def test_clim_defaults(self):
        car = VirtualCar()
        assert car.clim.fan == 0
        assert car.clim.auto == 0
        assert car.clim.dual == 0
        assert car.clim.ac == 1
        assert car.clim.enabled is False

    def test_dashboard_defaults(self):
        car = VirtualCar()
        assert car.dashboard.active is False
        for attr in ('airbag_pass', 'seatbelt', 'brakes', 'warn', 'stop',
                     'esp', 'tyre', 'low_beam'):
            assert getattr(car.dashboard, attr) == 0

    def test_radio_defaults(self):
        car = VirtualCar()
        assert car.radio.input == 'TUN'
        assert car.radio.volume == 15
        assert car.radio.volflag == 0xE0
        assert car.radio.audio['bass'] == 0x3F
        assert car.radio.audio['menu'] == 'none'

    def test_trip_defaults(self):
        car = VirtualCar()
        assert car.trip.fuel == 7.1
        assert car.trip.autonomy == 740
        assert len(car.trip.hist) == 2

    def test_kml_defaults(self):
        car = VirtualCar()
        assert car.kml.opt == 0
        assert car.kml.bits_223 == 0

    def test_bte_defaults(self):
        car = VirtualCar()
        assert car.bte.bits == 0

    def test_steering_wheel_defaults(self):
        car = VirtualCar()
        assert car.steering_wheel.active is False
        assert car.steering_wheel.volume == 15
        assert car.steering_wheel.volflag == 0xE0
        assert car.steering_wheel.angle == 0.0
        assert car.buttons is car.steering_wheel

    def test_buttons_defaults(self):
        car = VirtualCar()
        assert car.buttons.active is False
        assert car.buttons.volume == 15
        assert car.buttons.volflag == 0xE0
        assert car.buttons._volume_action_ticks == 0
        assert car.buttons.angle == 0.0
        for key in car.buttons.panel:
            assert car.buttons.panel[key] == 0

    def test_mfd_popup_defaults(self):
        car = VirtualCar()
        assert car.mfd_popup.flag == 0xFF
        assert car.mfd_popup.msg_id == 0x00
        assert car.mfd_popup.display_flags == 0xC6

    def test_bsi_new_fields_defaults(self):
        """New PSA-RE fields: blinkers and oil_level should have correct defaults."""
        car = VirtualCar()
        assert car.bsi.blinkers == 0       # no blinker
        assert car.bsi.oil_level == 0xFF   # invalid / not available

    def test_speed_control_defaults(self):
        """SpeedControl should start in NONE/STANDBY with no set_speed."""
        car = VirtualCar()
        assert car.speed_control.control_type == SpeedControl.NONE
        assert car.speed_control.function_status == SpeedControl.STANDBY
        assert car.speed_control.set_speed is None
        assert car.speed_control.partial_odo is None
        assert car.speed_control.unit_mph is False


class TestVirtualCarMutation:
    def test_bsi_state_mutation(self):
    """Subsystem state changes must persist on the car instance."""

    def test_bsi_mutation(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.reverse = 1
        car.bsi.rpm = 2500
        assert car.bsi.ignition_on is True
        assert car.bsi.reverse == 1
        assert car.bsi.rpm == 2500

    def test_doors_state_mutation(self):
    def test_clim_mutation(self):
        car = VirtualCar()
        car.clim.temp_left = 21.5
        car.clim.fan = 3
        assert car.clim.temp_left == 21.5
        assert car.clim.fan == 3

    def test_doors_mutation(self):
        car = VirtualCar()
        car.doors.front_left = 1
        car.doors.boot = 1
        car.doors.display_active = True
        assert car.doors.front_left == 1
        assert car.doors.boot == 1
        assert car.doors.display_active is True

    def test_tyres_state_mutation(self):
    def test_parktronic_mutation(self):
        car = VirtualCar()
        car.tyres.fl = Tyres.FLAT
        car.tyres.fr = Tyres.LOW
        car.tyres.display_active = True
        car.tyres.alert_0x168_b1 = 0xC0
        assert car.tyres.fl == Tyres.FLAT
        assert car.tyres.fr == Tyres.LOW
        assert car.tyres.display_active is True
        assert car.tyres.alert_0x168_b1 == 0xC0
        car.parktronic.rear_center = 2
        assert car.parktronic.rear_center == 2

    def test_tyres_constants(self):
        assert Tyres.OK == 0
        assert Tyres.LOW == 1
        assert Tyres.FLAT == 2
        assert Tyres.NO_DATA == 3

    def test_dashboard_active_flag(self):
    def test_tyres_mutation(self):
        car = VirtualCar()
        car.dashboard.active = True
        assert car.dashboard.active is True
        car.tyres.fl = Tyres.LOW
        assert car.tyres.fl == Tyres.LOW

    def test_parktronic_sensor_mutation(self):
    def test_dashboard_mutation(self):
        car = VirtualCar()
        car.parktronic.rear_left = 3
        car.parktronic.front_center = 1
        assert car.parktronic.rear_left == 3
        assert car.parktronic.front_center == 1
        car.dashboard.seatbelt = 1
        assert car.dashboard.seatbelt == 1

    def test_radio_mutation(self):
        car = VirtualCar()
        car.radio.input = 'CDC'
        car.radio.volume = 20
        car.radio.audio['bass'] = 0x45
        assert car.radio.input == 'CDC'
        assert car.radio.volume == 20
        assert car.radio.audio['bass'] == 0x45
        car.radio.input = 'CD'
        car.radio.volume = 18
        assert car.radio.input == 'CD'
        assert car.radio.volume == 18

    def test_trip_mutation(self):
        car = VirtualCar()
        car.trip.fuel = 9.5
        car.trip.hist[0]['speed'] = 50
        assert car.trip.fuel == 9.5
        assert car.trip.hist[0]['speed'] == 50
        car.trip.fuel = 8.5
        assert car.trip.fuel == 8.5

    def test_kml_mutation(self):
        car = VirtualCar()
        car.kml.opt = 1
        assert car.kml.opt == 1

    def test_bte_mutation(self):
        car = VirtualCar()
        car.bte.bits = 0x42
        assert car.bte.bits == 0x42

    def test_mfd_popup_mutation(self):
        car = VirtualCar()
        car.mfd_popup.flag = 0x80
        car.mfd_popup.msg_id = 0x42
        assert car.mfd_popup.flag == 0x80
        assert car.mfd_popup.msg_id == 0x42

    def test_buttons_mutation(self):
    def test_steering_wheel_mutation(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.volume = 22
        car.buttons.panel['source'] = 1
        assert car.buttons.active is True
        assert car.buttons.volume == 22
        assert car.buttons.panel['source'] == 1
        car.steering_wheel.active = True
        car.steering_wheel.volume = 22
        car.steering_wheel.set_angle(120.5)
        car.steering_wheel.panel['source'] = 1
        car.steering_wheel.panel['com_left'] = 1
        assert car.steering_wheel.active is True
        assert car.steering_wheel.volume == 22
        assert car.steering_wheel.angle == 120.5
        assert car.steering_wheel.panel['source'] == 1
        assert car.steering_wheel.panel['com_left'] == 1

    def test_buttons_press_sets_pulse(self):
        car = VirtualCar()
        car.buttons.press('source')
        assert car.buttons.panel['source'] == 1
        assert car.buttons._pulse_ticks['source'] == car.buttons._pulse_window
        car.buttons.press('com_right')
        assert car.buttons.panel['com_right'] == 1
        assert car.buttons._pulse_ticks['com_right'] == car.buttons._pulse_window

    def test_buttons_step_pulses_clears_after_window(self):
        car = VirtualCar()
        car.buttons.press('next')
        for _ in range(car.buttons._pulse_window):
            car.buttons.step_pulses()
        assert car.buttons.panel['next'] == 0

    def test_buttons_step_volume_resets_volflag(self):
        car = VirtualCar()
        car.buttons.volflag = 0x00
        car.buttons._volume_action_ticks = 1
        car.buttons.step_volume()
        assert car.buttons.volflag == 0xE0


class TestVirtualCarIsolation:
    """Each VirtualCar instance has independent state."""

    def test_two_cars_are_independent(self):
        car_a = VirtualCar()
        car_b = VirtualCar()
        car_a.bsi.ignition_on = True
        car_a.tyres.fl = Tyres.FLAT
        assert car_b.bsi.ignition_on is False
        assert car_b.tyres.fl == Tyres.OK
