import can
import datetime
import time
import threading
import sched
import queue

class CanRunner():
    def __init__(self, channel='can0', interface='socketcan', bitrate=125000, monitor=False):
        self.monitor = monitor
        self.bus = can.Bus(channel=channel, interface=interface, bitrate=bitrate)
        #can.interfaces.serial.serial_can.SerialBus(channel, baudrate=115200, timeout=0.1, rtscts=False, *args, **kwargs)
        #self.bus = can.Bus(channel='/dev/ttyACM0', interface='serial', bitrate=125000, baudrate=9600)
        self.sender = threading.Thread(target=self.sender)
        self.sender_exit = threading.Event()
        self.receiver = threading.Thread(target=self.receiver)
        self.receiver_exit = threading.Event()
        self.messages = []
        self.mess = []
        self.listeners = []
        self.modules = {}
        self.event_queue = queue.Queue()

    def reg(self, func, id, schedule, tp_id=None, tp_callback=None, *args, **kwargs):
        new_module = {
            'id': id,
            'timer': datetime.datetime.now(),
            'schedule': schedule/1000,
            'call': func,
            'tp_id': tp_id,
            'tp_callback': tp_callback
        }
        self.mess.append(new_module)

    def register(self, schedule, call):
        new_module = {
            'timer': datetime.datetime.now(),
            'schedule': schedule/1000,
            'call': call
        }
        self.messages.append(new_module)

    def receiver(self):
        while True:
            if self.receiver_exit.is_set():
                return
            recvd = self.bus.recv(1.0)
            if not recvd:
                continue

            for listener in self.listeners:
                if listener['id'] is None or listener['id'] == recvd.arbitration_id:
                    self.event_queue.put((listener['callback'], recvd))

            for message in self.mess:
                if message['tp_id'] == recvd['arbitration_id']:
                    self.event_queue.put((message['tp_callback'], recvd['data']))


    def process_events(self, dt=None):
        while True:
            try:
                callback, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(payload)
            except Exception as exc:
                print(f'CanRunner callback error: {exc}')

    def sender(self):
        while True:
            # If we need to exit
            if self.sender_exit.is_set():
                return

            for message in self.mess:
                now = datetime.datetime.now()
                if (now - message['timer']).total_seconds() >= message['schedule']:
                    data = message['call']()
                    if data != None and not self.monitor:
                        self.bus.send(can.Message(arbitration_id=message['id'], data=data, is_extended_id=False))
                    message['timer'] = now

            for message in self.messages:
                now = datetime.datetime.now()
                if (now - message['timer']).total_seconds() >= message['schedule']:
                    id, data = message['call']()
                    if data != None and not self.monitor:
                        self.bus.send(can.Message(arbitration_id=id, data=data, is_extended_id=False))
                    message['timer'] = now

            # Wait until next round
            time.sleep(0.02)

    def listen(self, can_id, callback):
        self.listeners.append({'id': can_id, 'callback': callback})

    def send_message(self, arbitration_id, data):
        if self.monitor or data is None:
            return
        self.bus.send(can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=False))

    def run(self):
        if not self.monitor:
            self.sender.start()
        self.receiver.start()

    def stop(self):
        self.sender_exit.set()
        self.receiver_exit.set()
