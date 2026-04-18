import datetime
import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Clim'
_version = '0.0.1'

class Clim(TabbedPanelItem):
    _ignition_on = 0x01

    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Clim'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/clim.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering radio calls')
        # Note: Msg1D0, Msg1E3, and Msg12D are registered by bsi-base and switch
        # to full climate encoding when car.clim.enabled is True.  No separate TX
        # registration is needed here.
        runner.car.clim.enabled = True

        # Initialise climate state on the shared VirtualCar.
        clim = runner.car.clim
        clim.fan = 0
        clim.dir_left = 0
        clim.dir_right = 0
        clim.temp_left = 0
        clim.temp_right = 0
        clim.unfrost_front = 0
        clim.unfrost_rear = 0
        clim.recycle = 0
        clim.auto = 0
        clim.dual = 0
        clim.bits = 0

        self.temp_disp = [
            'LO',
            '15',
            '16',
            '17',
            '18', '18.5',
            '19', '19.5',
            '20', '20.5',
            '21', '21.5',
            '22', '22.5',
            '23', '23.5',
            '24',
            '25',
            '26',
            '27',
            'HI'
        ]

        self._update_fan(clim.fan)
        self._update_temps()
        self._update_options()
        self._update_dir_buttons()

    @property
    def _clim(self):
        """Convenience accessor for the shared climate car state."""
        return self.runner.car.clim

    def _is_ignition_on(self):
        return bool(self.runner.car.bsi.ignition_on)

    def _set_off_state(self):
        clim = self._clim
        clim.fan = 0
        clim.dir_left = 0
        clim.dir_right = 0
        clim.bits = 0
        clim.unfrost_front = 0
        clim.unfrost_rear = 0
        clim.recycle = 0
        clim.auto = 0
        clim.dual = 0
        clim.temp_left = 0
        clim.temp_right = 0
        self._update_fan(clim.fan)
        self._update_temps()
        self._update_options()
        self._update_dir_buttons()

    def on_dir(self, seat, dir, state='down'):
        if state != 'down' or not self._is_ignition_on():
            return
        if seat == 0:
            self._clim.dir_left = dir
        else:
            self._clim.dir_right = dir

    def on_temp(self, zone, dir):
        if not self._is_ignition_on():
            return
        clim = self._clim
        temp = clim.temp_left if zone == 0 else clim.temp_right
        if not (temp == 0 and dir == -1) and not (temp == 20 and dir == +1):
            temp += dir
            if zone == 0:
                clim.temp_left = temp
            else:
                clim.temp_right = temp
            self.ids[f'cur_temp{zone}'].text = f'{self.temp_disp[temp]}c'

    def on_option(self, option, value):
        if not self._is_ignition_on():
            self._update_options()
            return
        setattr(self._clim, option, 1 if value == 'down' else 0)
        self._update_options()

    def on_fan(self, value):
        if not self._is_ignition_on():
            self._update_fan(self._clim.fan)
            return
        self._update_fan(self._normalize_fan(value))

    def on_toggle(self, bit, value):
        if not self._is_ignition_on():
            return
        if value == 'down':
            self._clim.bits |= 1 << bit
        else:
            self._clim.bits &= ~(1 << bit)

    def _normalize_fan(self, raw_value):
        if raw_value is None:
            return self._clim.fan
        fan = int(raw_value) & 0x0F
        return fan if 0 <= fan <= 8 else self._clim.fan

    def _normalize_dir(self, raw_value):
        if raw_value is None:
            return 0
        value = int(raw_value) & 0xFF
        return (value >> 4) if value > 0x0F else (value & 0x0F)

    def _update_fan(self, fan):
        self._clim.fan = fan
        if 'slider_fan' in self.ids and self.ids['slider_fan'].value != fan:
            self.ids['slider_fan'].value = fan
        if 'cur_fan' in self.ids:
            self.ids['cur_fan'].text = f'Fan: {fan}'

    def _update_dir_buttons(self):
        clim = self._clim
        dir_to_suffix = {
            0x03: 'fr',
            0x04: 'up',
            0x06: 'ud',
            0x02: 'down',
            0x05: 'fd',
            0x08: 'fast',
        }
        for seat, prefix in [(0, 'left'), (1, 'right')]:
            dir_val = self._normalize_dir(clim.dir_left if seat == 0 else clim.dir_right)
            target_suffix = dir_to_suffix.get(dir_val)
            target_id = f'{prefix}_{target_suffix}' if target_suffix else None
            for state_id in [f'{prefix}_fr', f'{prefix}_up', f'{prefix}_ud', f'{prefix}_down', f'{prefix}_fd', f'{prefix}_fast']:
                if state_id not in self.ids:
                    continue
                desired_state = 'down' if state_id == target_id else 'normal'
                if self.ids[state_id].state != desired_state:
                    self.ids[state_id].state = desired_state

    def _update_temps(self):
        clim = self._clim
        if 0 <= clim.temp_left < len(self.temp_disp):
            self.ids['cur_temp0'].text = f'{self.temp_disp[clim.temp_left]}c'
        if 0 <= clim.temp_right < len(self.temp_disp):
            self.ids['cur_temp1'].text = f'{self.temp_disp[clim.temp_right]}c'

    def _update_options(self):
        clim = self._clim
        if 'recycle' in self.ids:
            self.ids['recycle'].state = 'down' if clim.recycle else 'normal'
        if 'unfrost_front' in self.ids:
            self.ids['unfrost_front'].state = 'down' if clim.unfrost_front else 'normal'
        if 'unfrost_rear' in self.ids:
            self.ids['unfrost_rear'].state = 'down' if clim.unfrost_rear else 'normal'
        if 'auto' in self.ids:
            self.ids['auto'].state = 'down' if clim.auto else 'normal'
        if 'dual' in self.ids:
            self.ids['dual'].state = 'down' if clim.dual else 'normal'

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x036 and len(msg.data) >= 5:
            if int(msg.data[4]) != self._ignition_on:
                self._set_off_state()
        elif msg.arbitration_id == 0x1D0 and len(msg.data) >= 7:
            self._update_fan(self._normalize_fan(msg.data[2]))
            decoded_left = self._normalize_dir(msg.data[3])
            if decoded_left:
                self._clim.dir_left = decoded_left
            self._clim.recycle = (msg.data[4] >> 5) & 1
            self._clim.unfrost_front = (msg.data[4] >> 4) & 1
            self._clim.temp_left = msg.data[5]
            self._clim.temp_right = msg.data[6]
            self._update_temps()
            self._update_options()
            self._update_dir_buttons()
        elif msg.arbitration_id == 0x1E3 and len(msg.data) >= 7:
            self._update_fan(self._normalize_fan(msg.data[6]))
            self._clim.dir_left = msg.data[4] >> 4
            self._clim.dir_right = msg.data[5] >> 4
            self._clim.auto = (msg.data[0] >> 3) & 1
            self._clim.dual = msg.data[0] & 1
            self._clim.unfrost_front = (msg.data[1] >> 7) & 1
            self._clim.temp_left = msg.data[2] & 0x1F
            self._clim.temp_right = msg.data[3]
            self._update_temps()
            self._update_options()
            self._update_dir_buttons()

