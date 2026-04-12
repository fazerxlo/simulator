import datetime
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from can_messages import Msg165, Msg1A5, Msg1E5, Msg3E5


_modname = 'Radio_gen'
_modversion = '0.0.1'

class Radio_gen(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Radio/Gen'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/radio.kv')
        Builder.apply(self, 'Radio')

        # Register per-CAN-ID message objects.
        print('registering radio calls')
        runner.register_message(Msg165())
        runner.register_message(Msg1A5())
        runner.register_message(Msg3E5())
        runner.register_message(Msg1E5())

        runner.reg(self.can_test, 0x0A4, 100, tp_id=0x09F, tp_callback=self.can_test_tp)

        # Volume specific stuff (timer only — values live in car.radio)
        self.voltrig = None

        # Constant lookup tables kept on the module (not shared state).
        self.ambiances = ['none', 'classical', 'jazz-blues', 'pop-rock', 'vocal', 'techno']
        self.menus = ['none', 'ambiance', 'volume', 'lr-bal', 'rf-bal', 'loudness', 'treble', 'bass']

    @property
    def _radio(self):
        """Convenience accessor for the shared radio car state."""
        return self.runner.car.radio

    def reset_volume(self, dt):
        self._radio.volflag = 0xE0
        self.voltrig = None

    def on_volume(self, volume):
        if volume < 0:
            volume = 0
        if volume > 30:
            volume = 30
        self._radio.volflag = 0x00
        self._radio.volume = int(volume)
        self.ids['cur_vol'].text = f'{self._radio.volume}'
        if self.ids['slider_vol'].value != volume:
            self.ids['slider_vol'].value = volume
        if self.voltrig:
            self.voltrig.cancel()
        self.voltrig = Clock.schedule_once(self.reset_volume, 2)

    def on_panel(self, key, status):
        if key in self._radio.panel:
            self._radio.panel[key] = int(status == 'down')

    def on_input(self, input):
        self._radio.input = input

    def on_button(self, key):
        audio = self._radio.audio
        if key == 'audio':
            i = self.menus.index(audio['menu'])
            if i == len(self.menus)-1:
                i = 0
            else:
                i += 1
            audio['menu'] = self.menus[i]
            self.ids['cur_menu'].text = f'menu: {self.menus[i]}'

        if key == 'left':
            param = audio['menu']
            if param in ['lr-bal', 'rf-bal', 'bass', 'treble']:
                if not audio[param]-0x3F == -9:
                    audio[param] -= 1
                    self.ids[f'cur_param_{param}'].text = f'{param}: {audio[param]-0x3F}'
            elif param == 'loudness':
                audio[param] = 0x01
                self.ids[f'cur_param_{param}'].text = f'{param}: enabled'
            elif param == 'volume':
                audio[param] = 0x07
                self.ids[f'cur_param_{param}'].text = f'{param}: enabled'
            elif param == 'ambiance':
                i = self.ambiances.index(audio['ambiance'])
                if i != 0:
                    i -= 1
                else:
                    i = len(self.ambiances)-1
                audio['ambiance'] = self.ambiances[i]
                self.ids[f'cur_param_{param}'].text = f'{param}: {audio[param]}'

        if key == 'right':
            param = audio['menu']
            if param in ['lr-bal', 'rf-bal', 'bass', 'treble']:
                if not audio[param]-0x3F == 9:
                    audio[param] += 1
                    self.ids[f'cur_param_{param}'].text = f'{param}: {audio[param]-0x3F}'
            elif param == 'loudness' or param == 'volume':
                audio[param] = 0x00
                self.ids[f'cur_param_{param}'].text = f'{param}: disabled'
            elif param == 'ambiance':
                i = self.ambiances.index(audio['ambiance'])
                if i != len(self.ambiances)-1:
                    i += 1
                else:
                    i = 0
                audio['ambiance'] = self.ambiances[i]
                self.ids[f'cur_param_{param}'].text = f'{param}: {audio[param]}'

        if key == 'esc' and audio['menu'] != 'none':
            audio['menu'] = 'none'
            self.ids['cur_menu'].text = 'menu: none'

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x1A5 and len(msg.data) >= 1:
            # Msg1A5.decode() updated car.radio.volume; sync UI.
            self.on_volume(self._radio.volume)
        elif msg.arbitration_id == 0x165 and len(msg.data) >= 3:
            # Msg165.decode() updated car.radio.input; sync UI.
            pass
        elif msg.arbitration_id == 0x225 and len(msg.data) >= 5:
            self.band = msg.data[2]
            freq = (msg.data[3] << 8) | msg.data[4]
            self.on_freq(freq)
        elif msg.arbitration_id == 0x1E5 and len(msg.data) >= 7:
            # Msg1E5.decode() updated car.radio.audio; sync UI labels.
            audio = self._radio.audio
            self.ids['cur_menu'].text = f'menu: {audio["menu"]}'
            for param in ['ambiance', 'volume', 'lr-bal', 'rf-bal', 'loudness', 'treble', 'bass']:
                key = f'cur_param_{param}'
                if key in self.ids:
                    value = audio[param]
                    if param in ['lr-bal', 'rf-bal', 'bass', 'treble']:
                        value = value - 0x3F
                    self.ids[key].text = f'{param}: {value}'

    def can_test(self):
        return [0x01, 0x01, 0x00, 0x10, 0x00, 116, 101, 115]
