import os

from kivy.lang.builder import Builder
from kivy.uix.tabbedpanel import TabbedPanelItem

from generated.steering_wheel_messages import Msg0C5, Msg21F

_modname = 'Buttons'
_modversion = '0.0.1'


class Buttons(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Buttons'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/buttons.kv')
        Builder.apply(self)

        # Mark the steering wheel subsystem as active so Msg0C5 / Msg1A5 / Msg21F
        # encode from car.steering_wheel (car.buttons).
        runner.car.steering_wheel.active = True

        # Register steering wheel frames
        runner.register_message(Msg0C5())
        runner.register_message(Msg21F())

        self._button_ids = {f'btn_{k}': k for k in runner.car.steering_wheel.panel}

        self._sync_ui_from_state()

    @property
    def _buttons(self):
        """Convenience accessor for the shared steering wheel car state."""
        return self.runner.car.steering_wheel

    def _sync_ui_from_state(self):
        b = self._buttons
        for wid, key in self._button_ids.items():
            if wid in self.ids:
                desired = 'down' if b.panel.get(key) else 'normal'
                if self.ids[wid].state != desired:
                    self.ids[wid].state = desired
        self._update_pressed_label()
        if 'cur_angle' in self.ids and 'slider_angle' in self.ids:
            self.ids['slider_angle'].value = b.angle
            self.ids['cur_angle'].text = f'{b.angle:.1f}°'

    def _update_pressed_label(self):
        pressed = [k for k, v in self._buttons.panel.items() if v]
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
        b = self._buttons
        if key not in b.panel:
            return
        b.press(key)
        if key in b.REMOTE_ACTIONS:
            b.press_remote(key)
        self._set_button_state(key, True)
        self._update_pressed_label()

    def press_com(self, button):
        if hasattr(self.runner.car, 'trip'):
            self.runner.car.trip.press_com(button)
        b = self._buttons
        if button in b.panel:
            b.press(button)
            self._set_button_state(button, True)
        self._update_pressed_label()

    def on_angle(self, angle):
        self._buttons.set_angle(angle)
        if 'cur_angle' in self.ids:
            self.ids['cur_angle'].text = f'{angle:.1f}°'

    def pulse_volume(self, direction):
        b = self._buttons
        key = f'volume_{direction}'
        b.pulse_volume(direction)
        if key in b.panel:
            b.press(key)
            self._set_button_state(key, True)
            self._update_pressed_label()

    def on_can_message(self, msg):
        b = self._buttons
        if msg.arbitration_id == 0x0C5:
            if 'cur_angle' in self.ids and 'slider_angle' in self.ids:
                self.ids['slider_angle'].value = b.angle
                self.ids['cur_angle'].text = f'{b.angle:.1f}°'
            return

        if msg.arbitration_id == 0x21F:
            for key, value in b.panel.items():
                self._set_button_state(key, bool(value))
            self._update_pressed_label()
            return
