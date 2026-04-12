import datetime
import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Combine'
_version = '0.0.1'

class Combine(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Combine'
        self.runner = runner

        if not hasattr(self.runner, 'tyres_alert_0x168_b1'):
            self.runner.tyres_alert_0x168_b1 = 0

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/combine.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering radio calls')
        runner.register(100, self.can_combine_indicators)
        runner.register(100, self.can_combine_signals)

        self.options = {
            'airbag_pass': 0,
            'seatbelt': 0,
            'brakes': 0,
            'low_fuel': 0,
            'preheat': 0,
            'warn': 0,
            'stop': 0,
            'doors': 0,
            'esp': 0,
            'esp_blink': 0,
            'tyre': 0,
            'backlight': 0,
            'on': 0,
            'low_beam': 0,
            'high_beam': 0,
            'fog_front': 0,
            'fog_rear': 0,
            'clig_r': 0,
            'clig_l': 0,

            'coolant': 0,
            'oil_blink': 0,
            'coolant_blink': 0,
            'oil': 0,
            'abs': 0,
            'obd': 0,
            'gas_water': 0,
            'airbag': 0,
            'battery': 0,
            'dae': 0,
            'eco_blink': 0,
            'eco': 0,
            'battery_blink': 0,
            'obd_blink': 0,
        }

    def on_option(self, option, value):
        self.options[option] = 1 if value == 'down' else 0

    def can_combine_indicators(self):
        opt = self.options
        b0 = opt['airbag_pass']<<7 | opt['seatbelt']<<6 | opt['brakes']<<5 | opt['low_fuel']<<4 | opt['preheat']<<2
        b1 = opt['warn']<<7 | opt['stop']<<6 | opt['doors']<<4
        b2 = opt['esp']<<5 | opt['esp_blink']<<4
        b3 = opt['tyre']<<6
        b4 = opt['backlight']<<7 | opt['low_beam']<<6 | opt['high_beam']<<5 | opt['fog_front']<<4 | opt['fog_rear']<<3 | opt['clig_r']<<2 | opt['clig_l'] << 1
        b5 = opt['on']<<7
        return 0x128, [b0, b1, b2, b3, b4, b5, 0x00, 0x00]

    def can_combine_signals(self):
        opt = self.options
        b0 = opt['coolant']<<7 | opt['oil_blink']<<6 | opt['coolant_blink']<<5 | opt['oil']<<3
        tyre_overlay = int(getattr(self.runner, 'tyres_alert_0x168_b1', 0)) & 0xC0
        b1 = tyre_overlay if tyre_overlay else (opt['tyre']<<6)
        b3 = opt['abs']<<5 | opt['esp']<<4 | opt['obd']<<1 | opt['gas_water']
        b4 = opt['airbag']<<5 | opt['battery']<<1
        b6 = opt['dae']<<5 | opt['eco_blink']<<1 | opt['eco']
        b7 = opt['battery_blink']<<7 | opt['obd_blink']<<6
        return 0x168, [b0, b1, 0x00, b3, b4, 0x00, b6, b7]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x128 and len(msg.data) >= 6:
            data = msg.data
            self.options['airbag_pass'] = (data[0] >> 7) & 1
            self.options['seatbelt'] = (data[0] >> 6) & 1
            self.options['brakes'] = (data[0] >> 5) & 1
            self.options['low_fuel'] = (data[0] >> 4) & 1
            self.options['preheat'] = (data[0] >> 2) & 1
            self.options['warn'] = (data[1] >> 7) & 1
            self.options['stop'] = (data[1] >> 6) & 1
            self.options['doors'] = (data[1] >> 4) & 1
            self.options['esp'] = (data[2] >> 5) & 1
            self.options['esp_blink'] = (data[2] >> 4) & 1
            self.options['tyre'] = (data[3] >> 6) & 1
            self.options['backlight'] = (data[4] >> 7) & 1
            self.options['low_beam'] = (data[4] >> 6) & 1
            self.options['high_beam'] = (data[4] >> 5) & 1
            self.options['fog_front'] = (data[4] >> 4) & 1
            self.options['fog_rear'] = (data[4] >> 3) & 1
            self.options['clig_r'] = (data[4] >> 2) & 1
            self.options['clig_l'] = (data[4] >> 1) & 1
            self.options['on'] = (data[5] >> 7) & 1
            for key, value in self.options.items():
                if key in self.ids:
                    self.ids[key].state = 'down' if value else 'normal'
        elif msg.arbitration_id == 0x168 and len(msg.data) >= 8:
            data = msg.data
            self.options['coolant'] = (data[0] >> 7) & 1
            self.options['oil_blink'] = (data[0] >> 6) & 1
            self.options['coolant_blink'] = (data[0] >> 5) & 1
            self.options['oil'] = (data[0] >> 3) & 1
            self.options['tyre'] = (data[1] >> 6) & 1
            self.options['abs'] = (data[3] >> 5) & 1
            self.options['esp'] = (data[3] >> 4) & 1
            self.options['obd'] = (data[3] >> 1) & 1
            self.options['gas_water'] = data[3] & 1
            self.options['airbag'] = (data[4] >> 5) & 1
            self.options['battery'] = (data[4] >> 1) & 1
            self.options['dae'] = (data[6] >> 5) & 1
            self.options['eco_blink'] = (data[6] >> 1) & 1
            self.options['eco'] = data[6] & 1
            self.options['battery_blink'] = (data[7] >> 7) & 1
            self.options['obd_blink'] = (data[7] >> 6) & 1
            for key, value in self.options.items():
                if key in self.ids:
                    self.ids[key].state = 'down' if value else 'normal'
