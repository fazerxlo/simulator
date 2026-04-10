import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'CANMonitor'
_modversion = '0.1'

class CANMonitor(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'CAN Monitor'

        self.kv = Builder.load_file(os.path.join(os.path.dirname(__file__), 'can_monitor.kv'))
        Builder.apply(self)

        self.frames = []
        self.max_frames = 100
        runner.register_receive(self.on_frame)

    def on_frame(self, message):
        data_bytes = message.data if hasattr(message, 'data') else []
        formatted = ' '.join(f'{byte:02X}' for byte in data_bytes)
        entry = f"RX 0x{message.arbitration_id:03X} [{len(data_bytes)}] {formatted}"
        self.frames.insert(0, entry)
        if len(self.frames) > self.max_frames:
            self.frames.pop()
        Clock.schedule_once(self.update_view, 0)

    def update_view(self, dt):
        if self.ids.get('frame_list'):
            self.ids.frame_list.text = '\n'.join(self.frames)
