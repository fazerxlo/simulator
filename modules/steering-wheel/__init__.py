import logging
import os
import time

from kivy.clock import Clock
from kivy.lang.builder import Builder
from kivy.uix.tabbedpanel import TabbedPanelItem

from generated.steering_wheel_messages import Msg0C5, Msg21F
from stalk_controller import StalkButton, StalkEventType

_modname = 'SteeringWheel'
_modversion = '1.0.0'

logger = logging.getLogger(__name__)


class SteeringWheel(TabbedPanelItem):
    """Unified steering column controls & wheel angle UI module."""

    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Steering Wheel'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/steering_wheel.kv')
        Builder.apply(self)

        # Mark the steering wheel subsystem as active so Msg0C5 and Msg21F encode.
        runner.car.steering_wheel.active = True
        runner.car.steering_wheel.set_car(runner.car)

        # Register steering wheel frames
        runner.register_message(Msg0C5())
        runner.register_message(Msg21F())

        # Bind stalk state machine listener to sync UI on state changes
        runner.car.steering_wheel.sm.add_listener(self._on_stalk_event)

        self._button_map = {
            'volume_up': StalkButton.VOLUME_UP,
            'volume_down': StalkButton.VOLUME_DOWN,
            'src': StalkButton.SRC_BUTTON,
            'source': StalkButton.SRC_BUTTON,
            'seek_up': StalkButton.SEEK_UP,
            'next': StalkButton.SEEK_UP,
            'seek_down': StalkButton.SEEK_DOWN,
            'prev': StalkButton.SEEK_DOWN,
            'trip': StalkButton.TRIP_BUTTON,
            'com_right': StalkButton.TRIP_BUTTON,
            'voice_nav_repeat': StalkButton.VOICE_NAV_REPEAT,
            'com_left': StalkButton.VOICE_NAV_REPEAT,
        }

        self._sync_ui_from_state()

    @property
    def _sw(self):
        """Convenience accessor for the shared steering wheel car state."""
        return self.runner.car.steering_wheel

    def _sync_ui_from_state(self):
        sw = self._sw
        self._update_pressed_label()

        if 'cur_scroll' in self.ids:
            self.ids['cur_scroll'].text = f"Scroll: 0x{sw.scroll_counter:02X}"

        if 'cur_trip_screen' in self.ids and hasattr(self.runner.car, 'trip'):
            screens = ['Instant', 'Trip 1', 'Trip 2']
            scr_idx = getattr(self.runner.car.trip, 'screen', 0)
            scr_name = screens[scr_idx % len(screens)]
            self.ids['cur_trip_screen'].text = f"Trip: {scr_name}"

        if 'cur_angle' in self.ids and 'slider_angle' in self.ids:
            self.ids['slider_angle'].value = sw.angle
            self.ids['cur_angle'].text = f"{sw.angle:.1f}°"

    def _on_stalk_event(self, event):
        """Handle UI synchronization when state machine events occur."""
        self._sync_ui_from_state()

    def _update_pressed_label(self):
        pressed = [k for k, v in self._sw.panel.items() if v]
        if hasattr(self.runner.car, 'trip'):
            t = self.runner.car.trip
            if t.com_left and 'voice_nav_repeat' not in pressed:
                pressed.append('voice_nav_repeat')
            if t.com_right and 'trip' not in pressed:
                pressed.append('trip')
        if 'pressed_keys' in self.ids:
            self.ids['pressed_keys'].text = ', '.join(pressed) if pressed else '-'

    def _send_immediate_trip_frame(self):
        """Send an immediate CAN 0x221 frame so connected clusters/displays react instantaneously."""
        if hasattr(self.runner, 'send_message') and hasattr(self.runner.car, 'trip'):
            try:
                from generated.trip_messages import Msg221
                data = Msg221().encode(self.runner.car)
                if data:
                    self.runner.send_message(0x221, data)
            except Exception as exc:
                logger.error('Error sending immediate 0x221 frame: %s', exc)

    def _send_immediate_remote_frame(self):
        """Send an immediate CAN 0x21F frame so connected head units react instantaneously."""
        if hasattr(self.runner, 'send_message'):
            try:
                from generated.steering_wheel_messages import Msg21F
                data = Msg21F().encode(self.runner.car)
                if data:
                    self.runner.send_message(0x21F, data)
            except Exception as exc:
                logger.error('Error sending immediate 0x21F frame: %s', exc)

    def on_stalk_state(self, key, state):
        """Handle physical stalk button state changes ('down' or 'normal')."""
        if state == 'down':
            self.on_button_down(key)
        else:
            self.on_button_up(key)

    def on_button_down(self, key):
        """Handle physical button press down from UI."""
        btn = self._button_map.get(key)
        now_ms = time.monotonic() * 1000.0
        if btn:
            self._sw.sm.press_down(btn, time_ms=now_ms)
            if btn in (StalkButton.TRIP_BUTTON, StalkButton.VOICE_NAV_REPEAT):
                if hasattr(self.runner.car, 'trip'):
                    if btn == StalkButton.TRIP_BUTTON:
                        self.runner.car.trip.com_right = 1
                    else:
                        self.runner.car.trip.com_left = 1
                self._send_immediate_trip_frame()
            else:
                self._send_immediate_remote_frame()
        self._sync_ui_from_state()

    def on_button_up(self, key):
        """Handle physical button release from UI."""
        btn = self._button_map.get(key)
        now_ms = time.monotonic() * 1000.0
        if btn:
            self._sw.sm.release(btn, time_ms=now_ms)
            if btn in (StalkButton.TRIP_BUTTON, StalkButton.VOICE_NAV_REPEAT):
                if hasattr(self.runner.car, 'trip'):
                    if btn == StalkButton.TRIP_BUTTON:
                        self.runner.car.trip.com_right = 0
                        self.runner.car.trip._com_right_ticks = 0
                    else:
                        self.runner.car.trip.com_left = 0
                        self.runner.car.trip._com_left_ticks = 0
                self._send_immediate_trip_frame()
            else:
                self._send_immediate_remote_frame()
        self._sync_ui_from_state()

    def trigger_mute(self):
        """Trigger MUTE action via concurrent button trigger in state machine."""
        now_ms = time.monotonic() * 1000.0
        self._sw.sm.press_down(StalkButton.VOLUME_UP, time_ms=now_ms)
        self._sw.sm.press_down(StalkButton.VOLUME_DOWN, time_ms=now_ms)
        self._send_immediate_remote_frame()
        self._sw.sm.release(StalkButton.VOLUME_UP, time_ms=now_ms + 50.0)
        self._sw.sm.release(StalkButton.VOLUME_DOWN, time_ms=now_ms + 50.0)
        self._send_immediate_remote_frame()
        self._sync_ui_from_state()

    def on_scroll(self, direction):
        """Step the rotary encoder scroll position (CW=+1, CCW=-1)."""
        self._sw.rotary_scroll(direction, ticks=1)
        self._send_immediate_remote_frame()
        self._sync_ui_from_state()

    def on_angle(self, angle):
        """Update steering wheel angle."""
        self._sw.set_angle(angle)
        if hasattr(self.runner, 'send_message'):
            try:
                from generated.steering_wheel_messages import Msg0C5
                data = Msg0C5().encode(self.runner.car)
                if data:
                    self.runner.send_message(0x0C5, data)
            except Exception:
                pass
        if 'cur_angle' in self.ids:
            self.ids['cur_angle'].text = f"{angle:.1f}°"

    def press_key(self, key):
        """Backwards-compatible single button press trigger."""
        self.on_button_down(key)
        Clock.schedule_once(lambda _dt: self.on_button_up(key), 0.1)

    def press_com(self, button):
        """Backwards-compatible stalk commodores press trigger."""
        self.on_button_down(button)
        Clock.schedule_once(lambda _dt: self.on_button_up(button), 0.1)

    def pulse_volume(self, direction):
        """Backwards-compatible volume pulse helper."""
        key = 'volume_up' if direction == 'up' else 'volume_down'
        self.press_key(key)

    def on_can_message(self, msg):
        sw = self._sw
        if msg.arbitration_id == 0x0C5:
            if 'cur_angle' in self.ids and 'slider_angle' in self.ids:
                self.ids['slider_angle'].value = sw.angle
                self.ids['cur_angle'].text = f"{sw.angle:.1f}°"
            return

        if msg.arbitration_id == 0x21F:
            self._sync_ui_from_state()
            return
