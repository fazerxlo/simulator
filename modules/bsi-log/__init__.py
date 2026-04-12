import datetime
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from modules.messages_1a1 import messages

_modname = 'BSI_log'
_modversion = '0.0.1'

class BSI_log(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BSI/Log'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/bsi.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering BSI calls')
        runner.register(100, self.can_message)

        self.msg_flag = 0xFF
        self.msg_id = 0x00
        self.mess = 0x00

    def on_mess(self, mess):
        if mess < 0:
            mess = 0
        if mess > 0xff:
            mess = 0xff
        self.mess = int(mess)
        self.ids['cur_mess'].text = f'{self.mess}'
        if self.ids['slider_mess'].value != mess:
            self.ids['slider_mess'].value = mess
        if self.mess in messages:
            self.ids['send'].text = f'send {messages[self.mess]}'
        else:
            self.ids['send'].text = 'send (inconnu)'

    def show_msg(self, id=None):
        print(f'called with id={id} and flag={self.msg_flag}')
        if id and self.msg_flag == 0xFF:
            self.msg_id = int(id)
            self.msg_flag = 0x80
            Clock.schedule_once(self.show_msg, 2)
        elif id == self.msg_id and self.msg_flag != 0xFF:
            print('double call')
        elif self.msg_flag == 0x80:
            print('reset flag')
            self.msg_flag = 0x7F
            Clock.schedule_once(self.show_msg, 0.2)
        elif self.msg_flag == 0x7F:
            print('reset msg')
            self.msg_flag = 0xFF
            self.msg_id = 0x00

    def can_message(self):
        if getattr(self.runner, 'tyres_display_active', False):
            return 0x1A1, None
        if getattr(self.runner, 'doors_display_active', False):
            return 0x1A1, None
        if self.msg_flag == 0xFF:
            return 0x1A1, None
        b2 = 0xf0 if self.msg_flag != 0xFF else 0x00
        return 0x1A1, [self.msg_flag, self.msg_id, b2, 0x00, 0x00, 0x00, 0x00, 0x00]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x1A1 and len(msg.data) >= 2:
            self.msg_flag = msg.data[0]
            self.msg_id = msg.data[1]
            self.ids['cur_mess'].text = f'{self.msg_id}'
            if self.ids['slider_mess'].value != self.msg_id:
                self.ids['slider_mess'].value = self.msg_id
            if self.msg_id in messages:
                self.ids['send'].text = f'send {messages[self.msg_id]}'
            else:
                self.ids['send'].text = 'send (inconnu)'
