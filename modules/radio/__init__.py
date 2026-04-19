"""Unified radio / infotainment panel for the Peugeot 407 CAN2004 simulator.

Replaces the separate radio-gen, radio-fm, and radio-cd modules with a single
panel that:
  - Transmits all radio CAN frames (0x165, 0x1A5, 0x1E0, 0x1E5, 0x225, 0x265,
    0x2A5, 0x3E5) via the shared CanMessage object mechanism.
  - Decodes incoming frames and updates the shared car.radio state.
  - In monitor mode (runner.monitor == True) all interactive controls are
    disabled so the panel becomes read-only, showing live bus data only.

Signal documentation: doc/CAN2004_radio.md
"""

import logging
import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from can_messages import Msg165, Msg1A5, Msg1E0, Msg1E5, Msg225, Msg265, Msg2A5, Msg3E5

_modname = 'Radio'
_version = '1.0.0'

logger = logging.getLogger(__name__)


class Radio(TabbedPanelItem):
    """Unified radio / infotainment panel."""

    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Radio'
        self.runner = runner

        # Load KV file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/radio.kv')
        Builder.apply(self)

        # Register all radio CAN message objects.
        logger.debug('registering unified radio module')
        runner.register_message(Msg165())
        runner.register_message(Msg1A5())
        runner.register_message(Msg1E0())
        runner.register_message(Msg1E5())
        runner.register_message(Msg225())
        runner.register_message(Msg265())
        runner.register_message(Msg2A5())
        runner.register_message(Msg3E5())

        # Volume volflag reset timer handle.
        self.voltrig = None

        # Lookup tables for audio menu cycling and ambiance names.
        self.ambiances = ['none', 'classical', 'jazz-blues', 'pop-rock', 'vocal', 'techno']
        self.menus = ['none', 'ambiance', 'volume', 'lr-bal', 'rf-bal', 'loudness', 'treble', 'bass']

        # Apply monitor-mode read-only lock if needed.
        self._apply_monitor_lock()

    # ------------------------------------------------------------------
    # Convenience accessor
    # ------------------------------------------------------------------

    @property
    def _radio(self):
        """Shared radio car state."""
        return self.runner.car.radio

    # ------------------------------------------------------------------
    # Monitor-mode UI lock
    # ------------------------------------------------------------------

    def _apply_monitor_lock(self):
        """Disable all interactive controls when running in monitor mode."""
        if not getattr(self.runner, 'monitor', False):
            return
        interactive_ids = [
            'btn_vol_down', 'btn_vol_up', 'slider_vol',
            'btn_audio', 'btn_left', 'btn_right', 'btn_esc',
            'btn_ok', 'btn_up', 'btn_down',
            'btn_mode', 'btn_menu', 'btn_clim', 'btn_tel',
            'btn_trip',
            'slider_freq',
            'toggle_rds', 'toggle_pty', 'toggle_list',
            'toggle_scan', 'toggle_tun',
            'toggle_band_none', 'toggle_band_fm1', 'toggle_band_fm2',
            'toggle_band_fmast', 'toggle_band_am',
            'toggle_mem_no', 'toggle_mem_dash',
            'toggle_mem_1', 'toggle_mem_2', 'toggle_mem_3',
            'toggle_mem_4', 'toggle_mem_5', 'toggle_mem_6',
            'toggle_src_tun', 'toggle_src_cd', 'toggle_src_cdc',
            'toggle_src_aux1', 'toggle_src_aux2', 'toggle_src_usb',
            'toggle_src_bt',
        ]
        for wid in interactive_ids:
            if wid in self.ids:
                self.ids[wid].disabled = True

    # ------------------------------------------------------------------
    # Volume handlers
    # ------------------------------------------------------------------

    def reset_volume(self, dt):
        self._radio.volflag = 0xE0
        self.voltrig = None

    def on_volume(self, volume):
        volume = max(0, min(30, int(volume)))
        self._radio.volflag = 0x00
        self._radio.volume = volume
        if 'cur_vol' in self.ids:
            self.ids['cur_vol'].text = str(volume)
        if 'slider_vol' in self.ids and self.ids['slider_vol'].value != volume:
            self.ids['slider_vol'].value = volume
        if self.voltrig:
            self.voltrig.cancel()
        self.voltrig = Clock.schedule_once(self.reset_volume, 2)

    # ------------------------------------------------------------------
    # Source / input handlers
    # ------------------------------------------------------------------

    def on_input(self, src):
        self._radio.input = src

    # ------------------------------------------------------------------
    # Steering-wheel button handlers
    # ------------------------------------------------------------------

    def on_panel(self, key, status):
        if key in self._radio.panel:
            self._radio.panel[key] = int(status == 'down')

    def on_button(self, key):
        """Handle audio-menu cycling and left/right parameter adjustment."""
        audio = self._radio.audio
        if key == 'audio':
            i = self.menus.index(audio['menu'])
            i = (i + 1) % len(self.menus)
            audio['menu'] = self.menus[i]
            if 'cur_menu' in self.ids:
                self.ids['cur_menu'].text = f'menu: {self.menus[i]}'

        if key == 'left':
            param = audio['menu']
            if param in ('lr-bal', 'rf-bal', 'bass', 'treble'):
                if audio[param] - 0x3F > -9:
                    audio[param] -= 1
                    self._update_audio_label(param)
            elif param == 'loudness':
                audio[param] = 1
                self._update_audio_label(param)
            elif param == 'volume':
                audio[param] = 0x07
                self._update_audio_label(param)
            elif param == 'ambiance':
                i = self.ambiances.index(audio['ambiance'])
                audio['ambiance'] = self.ambiances[(i - 1) % len(self.ambiances)]
                self._update_audio_label(param)

        if key == 'right':
            param = audio['menu']
            if param in ('lr-bal', 'rf-bal', 'bass', 'treble'):
                if audio[param] - 0x3F < 9:
                    audio[param] += 1
                    self._update_audio_label(param)
            elif param in ('loudness', 'volume'):
                audio[param] = 0
                self._update_audio_label(param)
            elif param == 'ambiance':
                i = self.ambiances.index(audio['ambiance'])
                audio['ambiance'] = self.ambiances[(i + 1) % len(self.ambiances)]
                self._update_audio_label(param)

        if key == 'esc' and audio['menu'] != 'none':
            audio['menu'] = 'none'
            if 'cur_menu' in self.ids:
                self.ids['cur_menu'].text = 'menu: none'

    def _update_audio_label(self, param):
        key = f'cur_param_{param}'
        if key not in self.ids:
            return
        value = self._radio.audio[param]
        if param in ('lr-bal', 'rf-bal', 'bass', 'treble'):
            self.ids[key].text = f'{param}: {value - 0x3F}'
        elif param in ('loudness', 'volume'):
            self.ids[key].text = f'{param}: {"enabled" if value else "disabled"}'
        else:
            self.ids[key].text = f'{param}: {value}'

    # ------------------------------------------------------------------
    # FM tuner handlers
    # ------------------------------------------------------------------

    def on_freq(self, freq):
        freq = int(freq)
        self._radio.freq = freq
        disp = freq * 0.05 + 50
        if 'cur_freq' in self.ids:
            if self._radio.band == 0x50:
                self.ids['cur_freq'].text = f'{int(freq)} kHz'
            else:
                self.ids['cur_freq'].text = f'{disp:.2f} MHz'

    def on_band(self, state, value):
        if state == 'down' and value is not None:
            self._radio.band = int(value)
        self.on_freq(self._radio.freq)

    def on_toggle(self, var, state, value=None):
        if value is not None and state == 'down':
            setattr(self._radio, var, int(value))
        elif value is None:
            setattr(self._radio, var, int(state == 'down'))

    def on_mem(self, state, value):
        if state == 'down' and value is not None:
            self._radio.mem = int(value)

    # ------------------------------------------------------------------
    # Incoming CAN message handler (monitor + loopback)
    # ------------------------------------------------------------------

    def on_can_message(self, msg):
        aid = msg.arbitration_id
        data = msg.data

        if aid == 0x1A5 and len(data) >= 1:
            # Msg1A5.decode() already updated car.radio.volume; sync UI.
            self.on_volume(self._radio.volume)

        elif aid == 0x165 and len(data) >= 3:
            # Msg165.decode() updated car.radio.input; nothing more needed.
            pass

        elif aid == 0x225 and len(data) >= 5:
            # Msg225.decode() updated car.radio freq/band/flags; update display.
            self.on_freq(self._radio.freq)
            if 'cur_station' in self.ids:
                self.ids['cur_station'].text = self._radio.station_name

        elif aid == 0x2A5 and len(data) >= 1:
            # Msg2A5.decode() updated car.radio.station_name.
            if 'cur_station' in self.ids:
                self.ids['cur_station'].text = self._radio.station_name

        elif aid == 0x1E5 and len(data) >= 7:
            # Msg1E5.decode() updated car.radio.audio; refresh all labels.
            audio = self._radio.audio
            if 'cur_menu' in self.ids:
                self.ids['cur_menu'].text = f'menu: {audio["menu"]}'
            for param in ('ambiance', 'volume', 'lr-bal', 'rf-bal',
                          'loudness', 'treble', 'bass'):
                self._update_audio_label(param)
