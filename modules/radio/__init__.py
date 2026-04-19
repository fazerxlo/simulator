"""Unified radio / infotainment panel for the Peugeot 407 CAN2004 simulator.

Replaces the separate radio-gen, radio-fm, and radio-cd modules with a single
panel that:
  - Listens to all radio CAN frames (0x0A4, 0x165, 0x1A5, 0x1E0, 0x1E5,
    0x225, 0x265, 0x2A5, 0x3E5) and decodes them into shared car.radio state.
    The real
    workbench radio is the only transmitter of these frames; the simulator
    never sends them.
  - In monitor mode (runner.monitor == True) or regular simulator mode the
    radio panel is always read-only, reflecting what the real head unit is doing.

Signal documentation: doc/CAN2004_radio.md
"""

import logging
import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from generated.radio_messages import Msg0A4, Msg165, Msg1A5, Msg1E0, Msg1E5, Msg225, Msg265, Msg2A5, Msg3E5

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
        runner.register_message(Msg0A4())
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
        self._refresh_readouts()

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
            if self._radio.band == 0xD0:
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
    # UI toggle helpers (called from on_can_message to reflect bus state)
    # ------------------------------------------------------------------

    def _set_toggle_group(self, group_map, target_id):
        """Explicitly set every button in a group to 'down' or 'normal'.

        Kivy's ToggleButton only calls _release_group() from _do_press()
        (i.e. real user touch). Programmatic ``state = 'down'`` does NOT
        release sibling buttons, so we must set every button explicitly.
        """
        for btn_id in group_map.values():
            if btn_id in self.ids:
                self.ids[btn_id].state = 'down' if btn_id == target_id else 'normal'

    def _update_source_toggle(self):
        """Set the source toggle to match car.radio.input."""
        src_map = {
            'TUN': 'toggle_src_tun', 'CD': 'toggle_src_cd',
            'CDC': 'toggle_src_cdc', 'AUX1': 'toggle_src_aux1',
            'AUX2': 'toggle_src_aux2', 'USB': 'toggle_src_usb',
            'BT': 'toggle_src_bt',
        }
        self._set_toggle_group(src_map, src_map.get(self._radio.input))

    def _update_band_toggle(self):
        """Set the band toggle to match car.radio.band."""
        band_map = {
            0x00: 'toggle_band_none', 0x90: 'toggle_band_fm1',
            0xA0: 'toggle_band_fm2', 0xC0: 'toggle_band_fmast',
            0xD0: 'toggle_band_am',
        }
        self._set_toggle_group(band_map, band_map.get(self._radio.band) or band_map[0x00])

    def _update_mem_toggle(self):
        """Set the memory preset toggle to match car.radio.mem."""
        mem_map = {
            0x00: 'toggle_mem_no', 0x10: 'toggle_mem_1',
            0x20: 'toggle_mem_2', 0x30: 'toggle_mem_3',
            0x40: 'toggle_mem_4', 0x50: 'toggle_mem_5',
            0x60: 'toggle_mem_6', 0x70: 'toggle_mem_dash',
        }
        self._set_toggle_group(mem_map, mem_map.get(self._radio.mem) or mem_map[0x00])

    def _update_flag_toggles(self):
        """Sync RDS/PTY/TA/scan/tun/list toggle states from car.radio."""
        r = self._radio
        flags = {
            'toggle_rds': r.rds, 'toggle_pty': r.pty, 'toggle_ta': r.ta,
            'toggle_list': r.list_flag, 'toggle_scan': r.scan, 'toggle_tun': r.tun,
        }
        for btn_id, value in flags.items():
            if btn_id in self.ids:
                self.ids[btn_id].state = 'down' if value else 'normal'

    def _refresh_readouts(self):
        """Populate the visible station / RadioText readouts from shared state."""
        if 'cur_vol' in self.ids:
            self.ids['cur_vol'].text = str(self._radio.volume)
        if 'slider_vol' in self.ids:
            self.ids['slider_vol'].value = self._radio.volume
        if 'cur_station' in self.ids:
            self.ids['cur_station'].text = self._radio.station_name or ''
        if 'cur_rds_text' in self.ids:
            self.ids['cur_rds_text'].text = self._radio.rds_text or ''
        self.on_freq(self._radio.freq)
        self._update_source_toggle()
        self._update_band_toggle()
        self._update_mem_toggle()
        self._update_flag_toggles()

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
            # Msg165.decode() updated car.radio.input; sync source toggles.
            self._update_source_toggle()

        elif aid == 0x225 and len(data) >= 5:
            # Msg225.decode() updated car.radio freq/band/flags; update display.
            self.on_freq(self._radio.freq)
            if 'cur_station' in self.ids:
                self.ids['cur_station'].text = self._radio.station_name
            self._update_band_toggle()
            self._update_mem_toggle()
            self._update_flag_toggles()

        elif aid == 0x2A5 and len(data) >= 1:
            # Msg2A5.decode() updated car.radio.station_name.
            if 'cur_station' in self.ids:
                self.ids['cur_station'].text = self._radio.station_name

        elif aid == 0x0A4 and len(data) >= 2:
            # Msg0A4.decode() updated car.radio.rds_text (RadioText / RT).
            if 'cur_rds_text' in self.ids:
                self.ids['cur_rds_text'].text = self._radio.rds_text

        elif aid == 0x265 and len(data) >= 1:
            # Msg265 carries RDS status flags; flag toggles already updated
            # by _update_flag_toggles() when a 0x225 frame arrives.
            pass

        elif aid == 0x1E5 and len(data) >= 7:
            # Msg1E5.decode() updated car.radio.audio; refresh all labels.
            audio = self._radio.audio
            if 'cur_menu' in self.ids:
                self.ids['cur_menu'].text = f'menu: {audio["menu"]}'
            for param in ('ambiance', 'volume', 'lr-bal', 'rf-bal',
                          'loudness', 'treble', 'bass'):
                self._update_audio_label(param)
