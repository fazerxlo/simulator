"""
Virtual car state for the Peugeot 407 CAN 2004 simulator.

Each car subsystem has a dedicated state object. Modules update these
objects; CAN frame encoders read from them to produce bus traffic.

This design ensures each CAN ID has exactly one source of truth even
when multiple UI modules are loaded simultaneously, eliminating the
message-conflict problem described in the project structure issue.
"""


class BSI:
    """Body Systems Interface and drivetrain state."""

    def __init__(self):
        self.ignition_on = False
        self.power_mode = 0x02
        self.economy = 0
        self.dash_lights = 0
        self.dark_mode = 0
        self.lum = 10
        self.engine_running = 0
        # 0 = off, 1 = side, 2 = low beam, 3 = high beam
        self.light_mode = 0
        self.rpm = 0
        self.speed = 0
        self.fuel = 0
        self.oil = 0
        self.coolant = 0
        self.temperature = 20
        self.reverse = 0


class Clim:
    """Climate control state."""

    def __init__(self):
        self.fan = 0
        self.dir_left = 0
        self.dir_right = 0
        self.temp_left = 0
        self.temp_right = 0
        self.unfrost_front = 0
        self.unfrost_rear = 0
        self.recycle = 0
        self.auto = 0
        self.dual = 0
        self.bits = 0


class Doors:
    """Door and panel opening state."""

    def __init__(self):
        self.front_left = 0
        self.front_right = 0
        self.rear_left = 0
        self.rear_right = 0
        self.boot = 0
        self.bonnet = 0
        self.rear_window = 0
        self.fuel_flap = 0
        # True while a door-open popup is being displayed on the MFD
        self.display_active = False


class Parktronic:
    """Parking sensor distances and activation state."""

    def __init__(self):
        self.display = 0
        self.front_active = 0
        self.rear_active = 0
        # Sensor values: 7 = inactive / no object, 0 = closest
        self.rear_left = 7
        self.rear_center = 7
        self.rear_right = 7
        self.front_left = 7
        self.front_center = 7
        self.front_right = 7


class Tyres:
    """Tyre pressure monitoring state."""

    # Tyre condition constants
    OK = 0
    LOW = 1
    FLAT = 2
    NO_DATA = 3

    def __init__(self):
        self.fl = Tyres.OK
        self.fr = Tyres.OK
        self.rl = Tyres.OK
        self.rr = Tyres.OK
        # True while a tyre-warning popup is being displayed on the MFD
        self.display_active = False
        # Byte 1 value for the 0x168 dashboard alert frame
        self.alert_0x168_b1 = 0


class Dashboard:
    """Combined dashboard indicator state (drives 0x128 and 0x168).

    The ``active`` flag is set by the combine module when it loads.
    When active, the combine module owns the 0x128 and 0x168 senders;
    bsi-base will skip registering 0x128 in that case.
    """

    def __init__(self):
        # 0x128 — cluster warning and lamp status
        self.airbag_pass = 0
        self.seatbelt = 0
        self.brakes = 0
        self.low_fuel = 0
        self.preheat = 0
        self.warn = 0
        self.stop = 0
        self.doors = 0
        self.esp = 0
        self.esp_blink = 0
        self.tyre = 0
        self.backlight = 0
        self.on = 0
        self.low_beam = 0
        self.high_beam = 0
        self.fog_front = 0
        self.fog_rear = 0
        self.clig_r = 0
        self.clig_l = 0
        # 0x168 — warning and signal lamps
        self.coolant_warn = 0
        self.oil_blink = 0
        self.coolant_blink = 0
        self.oil_warn = 0
        self.abs = 0
        self.obd = 0
        self.gas_water = 0
        self.airbag = 0
        self.battery = 0
        self.dae = 0
        self.eco_blink = 0
        self.eco = 0
        self.battery_blink = 0
        self.obd_blink = 0
        # True when the combine module is loaded and owns 0x128 / 0x168
        self.active = False


class VirtualCar:
    """Shared virtual car state for the Peugeot 407 simulator.

    Every simulation module receives a reference to this object and uses it
    to exchange state with other modules.  CAN frame senders encode bus
    traffic directly from this shared state, so each CAN ID has exactly
    one source of truth even when multiple UI modules are loaded at the
    same time.

    Usage::

        car = VirtualCar()
        runner = CanRunner(car=car)
        # modules receive runner and access car via runner.car
        bsi_module = BSI_base(runner)
        # bsi_module reads/writes runner.car.bsi.*
    """

    def __init__(self):
        self.bsi = BSI()
        self.clim = Clim()
        self.doors = Doors()
        self.parktronic = Parktronic()
        self.tyres = Tyres()
        self.dashboard = Dashboard()
