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

    def on_dir(self, seat, dir):
        if not self._is_ignition_on():
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
            return
        setattr(self._clim, option, 1 if value == 'down' else 0)

    def on_toggle(self, bit, value):
        if not self._is_ignition_on():
            return
        if value == 'down':
            self._clim.bits |= 1 << bit
        else:
            self._clim.bits &= ~(1 << bit)

    def can_clim_panel(self):
        if not self._is_ignition_on():
            return 0x1D0, None
        clim = self._clim
        b4 = clim.recycle << 5 | clim.unfrost_front << 4
        return 0x1D0, [0x00, 0x00, clim.fan, clim.dir_left, b4, clim.temp_left, clim.temp_right]

    def can_clim_cmd(self):
        if not self._is_ignition_on():
            return 0x12D, None
        return 0x12D, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def can_clim_emf(self):
        if not self._is_ignition_on():
            return 0x1E3, None
        clim = self._clim
        # recycle, ac off, off, auto air, auto (text), hide fan, ext air, dual
        b1 = clim.auto << 3 | clim.dual
        # unfrost front, [3 bits] temperature offset, 4 bits unknown
        b2 = clim.unfrost_front << 7
        b3 = clim.bits | clim.temp_left  # unknown, 2 bits: if both 1: '--.-', 5 bits temperature // left seat + dual
        b4 = clim.temp_right  # same as b4, right seat only
        b5 = clim.dir_left << 4  # 4 bits: direction, 4 bits unknown // left seat + dual
        b6 = clim.dir_right << 4  # 4 bits: direction, 4 bits unknown // right seat only
        b7 = clim.fan  # 4 unknown, 4 bits: fan
        return 0x1E3, [b1, b2, b3, b4, b5, b6, b7]

    def _normalize_fan(self, raw_value):
        if raw_value is None:
            return self._clim.fan
        fan = int(raw_value) & 0x0F
        return fan if 0 <= fan <= 8 else self._clim.fan

    def _update_fan(self, fan):
        self._clim.fan = fan
        if 'slider_fan' in self.ids and self.ids['slider_fan'].value != fan:
            self.ids['slider_fan'].value = fan
        if 'cur_fan' in self.ids:
            self.ids['cur_fan'].text = f'Fan: {fan}'

    def _update_dir_buttons(self):
        clim = self._clim
        for seat, prefix in [(0, 'left'), (1, 'right')]:
            for state_id in [f'{prefix}_fr', f'{prefix}_up', f'{prefix}_ud', f'{prefix}_down', f'{prefix}_fd', f'{prefix}_fast']:
                if state_id in self.ids:
                    self.ids[state_id].state = 'normal'
            dir_val = clim.dir_left if seat == 0 else clim.dir_right
            if dir_val == 0x03 and f'{prefix}_fr' in self.ids:
                self.ids[f'{prefix}_fr'].state = 'down'
            elif dir_val == 0x04 and f'{prefix}_up' in self.ids:
                self.ids[f'{prefix}_up'].state = 'down'
            elif dir_val == 0x06 and f'{prefix}_ud' in self.ids:
                self.ids[f'{prefix}_ud'].state = 'down'
            elif dir_val == 0x02 and f'{prefix}_down' in self.ids:
                self.ids[f'{prefix}_down'].state = 'down'
            elif dir_val == 0x05 and f'{prefix}_fd' in self.ids:
                self.ids[f'{prefix}_fd'].state = 'down'
            elif dir_val == 0x01 and f'{prefix}_fast' in self.ids:
                self.ids[f'{prefix}_fast'].state = 'down'
            elif dir_val == 0x08:
                # Auto airflow mode does not map to a single manual direction button.
                pass

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
            self._clim.dir_left = msg.data[3]
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

