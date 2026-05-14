import can
import datetime
import logging
import time
import threading
import sched
import queue

from car_state import VirtualCar

logger = logging.getLogger(__name__)

class CanRunner():
    PRE_IGNITION_ALLOWED_IDS = {0x036, 0x110, 0x190, 0x1D0, 0x1E3, 0x217, 0x52D}
    # Small timing lead so periodic frames can land up to ~5% earlier than the
    # measured workbench cadence, compensating for thread jitter without making
    # the simulator visibly faster than the bench.
    SCHEDULE_ADVANCE_FACTOR = 0.95
    SENDER_SLEEP_S = 0.005

    def __init__(self, channel='vcan0', interface='socketcan', bitrate=125000, monitor=False, can_version='2004'):
        self.monitor = monitor
        self.can_version = can_version
        self.channel = channel
        self.interface = interface
        self.bitrate = bitrate
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
        self.enabled_modules = set()
        self.event_queue = queue.Queue()

        # Shared virtual-car state.  All modules read and write car state
        # through this object rather than storing ad-hoc attributes on the
        # runner, keeping each subsystem's state in one authoritative place.
        self.car = VirtualCar()

        # Track which callable "owns" each CAN ID so duplicate registrations
        # can be detected and reported early.
        self._can_id_owners: dict = {}

        # CanMessage objects registered via register_message().
        # Keys are CAN arbitration IDs; values are CanMessage instances.
        self._can_message_objects: dict = {}
        self._message_object_timers: dict = {}

        # Transient SocketCAN/slcan backpressure can happen on a busy bench or
        # when the adapter/bus is not ready to accept another frame yet.
        # Track the error state per arbitration ID so one temporary failure on
        # one frame does not suppress the entire keepalive set.
        self._tx_error_state: dict = {}

    def set_enabled_modules(self, modules):
        self.enabled_modules = {str(module) for module in modules}

    def is_module_enabled(self, module_name):
        return module_name in self.enabled_modules

    def message_enabled(self, msg):
        required_modules = getattr(msg, 'required_modules', frozenset())
        if not required_modules:
            return True
        return any(module_name in self.enabled_modules for module_name in required_modules)

    # ------------------------------------------------------------------
    # Backward-compatibility properties
    # Existing modules that accessed runner.ignition_on / runner.power_mode /
    # runner.reverse directly continue to work; the values are now stored in
    # runner.car.bsi.* and these properties are thin delegating wrappers.
    # ------------------------------------------------------------------

    @property
    def ignition_on(self):
        return self.car.bsi.ignition_on

    @ignition_on.setter
    def ignition_on(self, value):
        self.car.bsi.ignition_on = value

    @property
    def power_mode(self):
        return self.car.bsi.power_mode

    @power_mode.setter
    def power_mode(self, value):
        self.car.bsi.power_mode = value

    @property
    def reverse(self):
        return self.car.bsi.reverse

    @reverse.setter
    def reverse(self, value):
        self.car.bsi.reverse = value

    # Cross-module display-arbitration flags (stored in car sub-objects,
    # exposed here for backward compatibility with existing module code).

    @property
    def tyres_display_active(self):
        return self.car.tyres.display_active

    @tyres_display_active.setter
    def tyres_display_active(self, value):
        self.car.tyres.display_active = value

    @property
    def doors_display_active(self):
        return self.car.doors.display_active

    @doors_display_active.setter
    def doors_display_active(self, value):
        self.car.doors.display_active = value

    @property
    def tyres_alert_0x168_b1(self):
        return self.car.tyres.alert_0x168_b1

    @tyres_alert_0x168_b1.setter
    def tyres_alert_0x168_b1(self, value):
        self.car.tyres.alert_0x168_b1 = value

    @property
    def combine_active_0x168(self):
        return self.car.dashboard.active

    @combine_active_0x168.setter
    def combine_active_0x168(self, value):
        self.car.dashboard.active = value

    def can_send(self, arbitration_id, data):
        if data is None:
            return False
        # Support realistic cold-start pre-ignition traffic while preventing full-bus spam.
        if not self.ignition_on and arbitration_id not in self.PRE_IGNITION_ALLOWED_IDS:
            return False
        return True

    def reg(self, func, id, schedule, tp_id=None, tp_callback=None, *args, **kwargs):
        if id in self._can_id_owners:
            existing = self._can_id_owners[id]
            logger.warning(
                'CAN ID 0x%03X already registered by %s, now overridden by %s',
                id, getattr(existing, '__qualname__', existing),
                getattr(func, '__qualname__', func),
            )
        self._can_id_owners[id] = func
        new_module = {
            'id': id,
            'timer': datetime.datetime.now(),
            'schedule': schedule/1000,
            'call': func,
            'tp_id': tp_id,
            'tp_callback': tp_callback
        }
        self.mess.append(new_module)

    def _safe_send(self, arbitration_id, data):
        if self.monitor or not self.can_send(arbitration_id, data):
            return None

        state = self._tx_error_state.setdefault(
            arbitration_id,
            {'count': 0, 'last_error': None, 'backoff_until': 0.0},
        )

        now = time.monotonic()
        if now < state['backoff_until']:
            return False

        message = can.Message(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=False,
        )

        try:
            try:
                self.bus.send(message, timeout=0.05)
            except TypeError:
                self.bus.send(message)
            state['count'] = 0
            state['last_error'] = None
            state['backoff_until'] = 0.0
            logger.debug(
                'TX 0x%03X  %s',
                arbitration_id,
                ' '.join(f'{b:02X}' for b in data),
            )
            return True
        except can.CanError as exc:
            state['count'] += 1
            err_text = str(exc)
            backoff_s = min(0.05, 0.005 * state['count'])
            if 'buffer' in err_text.lower() or 'space available' in err_text.lower():
                state['backoff_until'] = time.monotonic() + backoff_s
            else:
                state['backoff_until'] = 0.0
            should_log = err_text != state['last_error'] or state['count'] in (1, 10, 50, 100)
            if should_log:
                print(
                    f'CanRunner TX warning for 0x{arbitration_id:03X}: '
                    f'{exc} (retrying after {int(backoff_s * 1000)} ms)'
                )
            state['last_error'] = err_text
            return False

    def register(self, schedule, call):
        new_module = {
            'timer': datetime.datetime.now(),
            'schedule': schedule/1000,
            'call': call
        }
        self.messages.append(new_module)

    def register_message(self, msg):
        """Register a :class:`~generated.base.CanMessage` object as the periodic
        sender for its CAN arbitration ID.

        Only one object may own each ID.  A second registration for the same
        ID logs a warning and the new object takes over (last writer wins).
        """
        can_id = msg.can_id
        if can_id in self._can_message_objects:
            existing = self._can_message_objects[can_id]
            logger.warning(
                'CAN ID 0x%03X already owned by %s, overriding with %s',
                can_id, type(existing).__name__, type(msg).__name__,
            )
        self._can_message_objects[can_id] = msg
        self._message_object_timers[can_id] = datetime.datetime.now()

    def receiver(self):
        while True:
            if self.receiver_exit.is_set():
                return
            recvd = self.bus.recv(1.0)
            if not recvd:
                continue

            logger.debug(
                'RX 0x%03X  %s',
                recvd.arbitration_id,
                ' '.join(f'{b:02X}' for b in recvd.data),
            )

            for listener in self.listeners:
                if listener['id'] is None or listener['id'] == recvd.arbitration_id:
                    self.event_queue.put((listener['callback'], recvd))

            for message in self.mess:
                if message['tp_id'] == recvd['arbitration_id']:
                    self.event_queue.put((message['tp_callback'], recvd['data']))

            # Call decode() on the matching CanMessage object (if any) so that
            # car state is updated from the received frame.
            msg_obj = self._can_message_objects.get(recvd.arbitration_id)
            if msg_obj is not None:
                try:
                    msg_obj.decode(self.car, recvd.data)
                except Exception as exc:
                    logger.error('CanRunner decode error for 0x%03X: %s', recvd.arbitration_id, exc)


    def process_events(self, dt=None):
        while True:
            try:
                callback, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(payload)
            except Exception as exc:
                logger.error('CanRunner callback error: %s', exc)

    def _period_due(self, elapsed_s, period_ms):
        target_s = max(0.001, (max(1, int(period_ms)) / 1000.0) * self.SCHEDULE_ADVANCE_FACTOR)
        return elapsed_s >= target_s

    def sender(self):
        while True:
            # If we need to exit
            if self.sender_exit.is_set():
                return

            for message in self.mess:
                now = datetime.datetime.now()
                if self._period_due((now - message['timer']).total_seconds(), int(message['schedule'] * 1000)):
                    data = message['call']()
                    send_result = self._safe_send(message['id'], data)
                    if send_result is not False:
                        message['timer'] = now

            for message in self.messages:
                now = datetime.datetime.now()
                if self._period_due((now - message['timer']).total_seconds(), int(message['schedule'] * 1000)):
                    id, data = message['call']()
                    send_result = self._safe_send(id, data)
                    if send_result is not False:
                        message['timer'] = now

            # CanMessage objects registered via register_message().
            for can_id, msg_obj in list(self._can_message_objects.items()):
                if not self.message_enabled(msg_obj):
                    continue
                if getattr(msg_obj, 'listen_only', False):
                    continue
                now = datetime.datetime.now()
                timer = self._message_object_timers.get(can_id, now)
                try:
                    active_period_ms = max(1, int(msg_obj.get_period_ms(self.car)))
                except Exception as exc:
                    logger.error('CanRunner period error for 0x%03X: %s', can_id, exc)
                    active_period_ms = max(1, int(getattr(msg_obj, 'period_ms', 100)))
                if self._period_due((now - timer).total_seconds(), active_period_ms):
                    try:
                        data = msg_obj.encode(self.car)
                    except Exception as exc:
                        logger.error('CanRunner encode error for 0x%03X: %s', can_id, exc)
                        data = None
                    send_result = self._safe_send(can_id, data)
                    if send_result is not False:
                        self._message_object_timers[can_id] = now

            # Wait until next round
            time.sleep(self.SENDER_SLEEP_S)

    def listen(self, can_id, callback):
        self.listeners.append({'id': can_id, 'callback': callback})

    def send_message(self, arbitration_id, data):
        self._safe_send(arbitration_id, data)

    def run(self):
        if not self.monitor:
            self.sender.start()
        self.receiver.start()

    def stop(self):
        self.sender_exit.set()
        self.receiver_exit.set()
