import os

from kivy.lang.builder import Builder
from kivy.uix.tabbedpanel import TabbedPanelItem

from generated.steering_wheel_messages import Msg0C5, Msg21F

_modname = 'SteeringWheel'
_modversion = '0.0.1'


class SteeringWheel(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Steering Wheel'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/steering_wheel.kv')
        Builder.apply(self)

        # Mark the steering wheel subsystem as active so Msg0C5 / Msg1A5 / Msg21F
        # encode from car.steering_wheel.
        runner.car.steering_wheel.active = True

        # Register steering wheel frames
        runner.register_message(Msg0C5())
        runner.register_message(Msg21F())

        self._button_ids = {f'btn_{k}': k for k in runner.car.steering_wheel.panel}

        self._sync_ui_from_state()

    @property
    def _sw(self):
        """Convenience accessor for the shared steering wheel car state."""
        return self.runner.car.steering_wheel

    def _sync_ui_from_state(self):
        sw = self._sw
        for wid, key in self._button_ids.items():
            if wid in self.ids:
                desired = 'down' if sw.panel.get(key) else 'normal'
                if self.ids[wid].state != desired:
                    self.ids[wid].state = desired
        self._update_pressed_label()
        if 'cur_vol' in self.ids:
            self.ids['cur_vol'].text = f'volume: {sw.volume}'
        if 'cur_angle' in self.ids and 'slider_angle' in self.ids:
            self.ids['slider_angle'].value = sw.angle
            self.ids['cur_angle'].text = f'{sw.angle:.1f}°'

    def _update_pressed_label(self):
        pressed = [k for k, v in self._sw.panel.items() if v]
        # Also check stalk com buttons from trip state if available
        if hasattr(self.runner.car, 'trip'):
            t = self.runner.car.trip
            if t.com_left and 'com_left' not in pressed:
                pressed.append('com_left')
            if t.com_right and 'com_right' not in pressed:
                pressed.append('com_right')
        self.ids['pressed_keys'].text = ', '.join(pressed) if pressed else '-'

    def _set_button_state(self, key, pressed):
        wid = f'btn_{key}'
        if wid in self.ids:
            desired = 'down' if pressed else 'normal'
            if self.ids[wid].state != desired:
                self.ids[wid].state = desired

    def press_key(self, key):
        sw = self._sw
        if key not in sw.panel:
            return
        sw.press(key)
        if key in sw.REMOTE_ACTIONS:
            sw.press_remote(key)
        self._set_button_state(key, True)
        self._update_pressed_label()

    def press_com(self, button):
        if hasattr(self.runner.car, 'trip'):
            self.runner.car.trip.press_com(button)
        sw = self._sw
        if button in sw.panel:
            sw.press(button)
            self._set_button_state(button, True)
        self._update_pressed_label()

    def on_angle(self, angle):
        self._sw.set_angle(angle)
        if 'cur_angle' in self.ids:
            self.ids['cur_angle'].text = f'{angle:.1f}°'

    def pulse_volume(self, direction):
        sw = self._sw
        key = f'volume_{direction}'
        sw.pulse_volume(direction)
        if key in sw.panel:
            sw.press(key)
            self._set_button_state(key, True)
            self._update_pressed_label()
        if 'cur_vol' in self.ids:
            self.ids['cur_vol'].text = f'volume: {sw.volume}'

    def on_can_message(self, msg):
        sw = self._sw
        if msg.arbitration_id == 0x1A5 and len(msg.data) >= 1:
            if 'cur_vol' in self.ids:
                self.ids['cur_vol'].text = f'volume: {sw.volume}'
            return

        if msg.arbitration_id == 0x0C5:
            if 'cur_angle' in self.ids and 'slider_angle' in self.ids:
                self.ids['slider_angle'].value = sw.angle
                self.ids['cur_angle'].text = f'{sw.angle:.1f}°'
            return

        if msg.arbitration_id == 0x21F:
            for key, value in sw.panel.items():
                self._set_button_state(key, bool(value))
            self._update_pressed_label()
            return

        if msg.arbitration_id != 0x3E5 or len(msg.data) < 6:
            return

        for key, value in sw.panel.items():
            self._set_button_state(key, bool(value))
        self._update_pressed_label()

