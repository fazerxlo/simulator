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
        runner.register(100, self.can_clim_panel)
        runner.register(100, self.can_clim_cmd)
        runner.register(100, self.can_clim_emf)

        self.fan = 0
        self.dir = [0,0]
        self.options = {
            'unfrost_front': 0,
            'unfrost_read': 0,
            'recycle': 0,
            'auto': 0,
            'dual': 0
        }
        self.temps = [0, 0]
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

        self.bits = 0

    def _is_ignition_on(self):
        return bool(getattr(self.runner, 'ignition_on', False))

    def _set_off_state(self):
        self.fan = 0
        self.dir = [0, 0]
        self.bits = 0
        self.options['unfrost_front'] = 0
        self.options['unfrost_read'] = 0
        self.options['recycle'] = 0
        self.options['auto'] = 0
        self.options['dual'] = 0
        self.temps = [0, 0]
        self._update_fan(self.fan)
        self._update_temps()
        self._update_options()
        self._update_dir_buttons()

    def on_dir(self, seat, dir):
        if not self._is_ignition_on():
            return
        self.dir[seat] = dir

    def on_temp(self, zone, dir):
        if not self._is_ignition_on():
            return
        if not (self.temps[zone] == 0 and dir == -1) and not (self.temps[zone] == 20 and dir == +1):
            self.temps[zone] += dir
            self.ids[f'cur_temp{zone}'].text = f'{self.temp_disp[self.temps[zone]]}c'

    def on_option(self, option, value):
        if not self._is_ignition_on():
            return
        self.options[option] = 1 if value == 'down' else 0

    def on_toggle(self, bit, value):
        if not self._is_ignition_on():
            return
        if value == 'down':
            self.bits |= 1<<bit
        else:
            self.bits &= ~(1<<bit)

    def can_clim_panel(self):
        if not self._is_ignition_on():
            return 0x1D0, None
        b4 = self.options['recycle']<<5 | self.options['unfrost_front']<<4
        return 0x1D0, [0x00, 0x00, self.fan, self.dir[0], b4, self.temps[0], self.temps[1]]

    def can_clim_cmd(self):
        if not self._is_ignition_on():
            return 0x12D, None
        return 0x12D, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def can_clim_emf(self):
        if not self._is_ignition_on():
            return 0x1E3, None
        # recycle, ac off, off, auto air, auto (text), hide fan, ext air, dual
        b1 = self.options['auto']<<3 | self.options['dual']
        # unfrost front, [3 bits] temperature offset, 4 bits unknown
        b2 = self.options['unfrost_front']<<7
        b3 = self.bits | self.temps[0] # unknown, 2 bits: if both 1: '--.-', 5 bits temperature // left seat + dual
        b4 = self.temps[1] # same as b4, right seat only
        b5 = self.dir[0]<<4 # 4 bits: direction, 4 bits unknown // left seat + dual
        b6 = self.dir[1]<<4 # 4 bits: direction, 4 bits unknown // right seat only
        b7 = self.fan # 4 unknown, 4 bits: fan
        return 0x1E3, [b1, b2, b3, b4, b5, b6, b7]

    def _normalize_fan(self, raw_value):
        if raw_value is None:
            return self.fan
        fan = int(raw_value) & 0x0F
        return fan if 0 <= fan <= 8 else self.fan

    def _update_fan(self, fan):
        self.fan = fan
        if 'slider_fan' in self.ids and self.ids['slider_fan'].value != fan:
            self.ids['slider_fan'].value = fan
        if 'cur_fan' in self.ids:
            self.ids['cur_fan'].text = f'Fan: {fan}'

    def _update_dir_buttons(self):
        for seat, prefix in [(0, 'left'), (1, 'right')]:
            for state_id in [f'{prefix}_fr', f'{prefix}_up', f'{prefix}_ud', f'{prefix}_down', f'{prefix}_fd', f'{prefix}_fast']:
                if state_id in self.ids:
                    self.ids[state_id].state = 'normal'
            if self.dir[seat] == 0x03 and f'{prefix}_fr' in self.ids:
                self.ids[f'{prefix}_fr'].state = 'down'
            elif self.dir[seat] == 0x04 and f'{prefix}_up' in self.ids:
                self.ids[f'{prefix}_up'].state = 'down'
            elif self.dir[seat] == 0x06 and f'{prefix}_ud' in self.ids:
                self.ids[f'{prefix}_ud'].state = 'down'
            elif self.dir[seat] == 0x02 and f'{prefix}_down' in self.ids:
                self.ids[f'{prefix}_down'].state = 'down'
            elif self.dir[seat] == 0x05 and f'{prefix}_fd' in self.ids:
                self.ids[f'{prefix}_fd'].state = 'down'
            elif self.dir[seat] == 0x01 and f'{prefix}_fast' in self.ids:
                self.ids[f'{prefix}_fast'].state = 'down'
            elif self.dir[seat] == 0x08:
                # Auto airflow mode does not map to a single manual direction button.
                pass

    def _update_temps(self):
        if 0 <= self.temps[0] < len(self.temp_disp):
            self.ids['cur_temp0'].text = f'{self.temp_disp[self.temps[0]]}c'
        if 0 <= self.temps[1] < len(self.temp_disp):
            self.ids['cur_temp1'].text = f'{self.temp_disp[self.temps[1]]}c'

    def _update_options(self):
        if 'recycle' in self.ids:
            self.ids['recycle'].state = 'down' if self.options['recycle'] else 'normal'
        if 'unfrost_front' in self.ids:
            self.ids['unfrost_front'].state = 'down' if self.options['unfrost_front'] else 'normal'
        if 'auto' in self.ids:
            self.ids['auto'].state = 'down' if self.options['auto'] else 'normal'
        if 'dual' in self.ids:
            self.ids['dual'].state = 'down' if self.options['dual'] else 'normal'

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x036 and len(msg.data) >= 5:
            if int(msg.data[4]) != self._ignition_on:
                self._set_off_state()
        elif msg.arbitration_id == 0x1D0 and len(msg.data) >= 7:
            self._update_fan(self._normalize_fan(msg.data[2]))
            self.dir[0] = msg.data[3]
            self.options['recycle'] = (msg.data[4] >> 5) & 1
            self.options['unfrost_front'] = (msg.data[4] >> 4) & 1
            self.temps[0] = msg.data[5]
            self.temps[1] = msg.data[6]
            self._update_temps()
            self._update_options()
            self._update_dir_buttons()
        elif msg.arbitration_id == 0x1E3 and len(msg.data) >= 7:
            self._update_fan(self._normalize_fan(msg.data[6]))
            self.dir[0] = msg.data[4] >> 4
            self.dir[1] = msg.data[5] >> 4
            self.options['auto'] = (msg.data[0] >> 3) & 1
            self.options['dual'] = msg.data[0] & 1
            self.options['unfrost_front'] = (msg.data[1] >> 7) & 1
            self.temps[0] = msg.data[2] & 0x1F
            self.temps[1] = msg.data[3]
            self._update_temps()
            self._update_options()
            self._update_dir_buttons()
