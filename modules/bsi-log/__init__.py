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
        # Note: Msg1A1 is registered by bsi-base.  This module drives the
        # mfd_popup state; show_msg() writes car.mfd_popup.flag / .msg_id.

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
        print(f'called with id={id} and flag={self.runner.car.mfd_popup.flag}')
        mfd = self.runner.car.mfd_popup
        if id is not None and mfd.flag in (0xFF, 0x00):
            mfd.msg_id = int(id)
            mfd.flag = 0x80
            Clock.schedule_once(self.show_msg, 2)
        elif id == mfd.msg_id and mfd.flag == 0x80:
            print('double call')
        elif mfd.flag == 0x80:
            print('reset flag')
            mfd.flag = 0x00
            Clock.schedule_once(self.show_msg, 0.2)
        elif mfd.flag == 0x00:
            print('reset msg')
            mfd.flag = 0xFF
            mfd.msg_id = 0x00

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x1A1 and len(msg.data) >= 2:
            # Msg1A1.decode() already updated car.mfd_popup; sync UI.
            mfd = self.runner.car.mfd_popup
            self.ids['cur_mess'].text = f'{mfd.msg_id}'
            if self.ids['slider_mess'].value != mfd.msg_id:
                self.ids['slider_mess'].value = mfd.msg_id
            if mfd.msg_id in messages:
                self.ids['send'].text = f'send {messages[mfd.msg_id]}'
            else:
                self.ids['send'].text = 'send (inconnu)'
