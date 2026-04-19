#!/usr/bin/env python3

import os
import sys
import argparse
import logging

# Kivy parses command-line arguments on import. Disable that behavior so
# simulator-specific flags like --channel and --monitor are handled here.
os.environ.setdefault('KIVY_NO_ARGS', '1')

import kivy
import can
import datetime
import time
import threading
import sched
import yaml
import importlib
from functools import partial

from kivy.app import App
from kivy.lang.builder import Builder
from kivy.clock import Clock

from can_runner import CanRunner


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('mode', nargs='?', choices=['monitor'], help='Run mode')
    parser.add_argument('--monitor', action='store_true', help='Monitor CAN bus only, do not send outgoing frames')
    parser.add_argument('--channel', default='vcan0', help='SocketCAN interface name, for example can0 or vcan0')
    parser.add_argument('--interface', default='socketcan', help='python-can backend interface')
    parser.add_argument('--bitrate', type=int, default=125000, help='CAN bitrate for the selected interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug output including raw CAN frame dumps')
    args, unknown = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + unknown
    return args


class PeugeotSim(App):
    def __init__(self, monitor=False, channel='vcan0', interface='socketcan', bitrate=125000, **kwargs):
        super().__init__(**kwargs)
        self.monitor = monitor
        self.channel = channel
        self.interface = interface
        self.bitrate = bitrate

    def build(self):
        return Builder.load_file('main.kv')

    def on_start(self):
        # Get tabs id
        tabs = self.root.ids['modules']
        tabs.clear_widgets()

        with open('config.yml', 'r') as conf_file:
            self.conf = yaml.load(conf_file, Loader=yaml.FullLoader)

        # Init CAN runner
        self.can_runner = CanRunner(
            channel=self.channel,
            interface=self.interface,
            bitrate=self.bitrate,
            monitor=self.monitor,
        )
        self.can_runner.set_enabled_modules(self.conf.get('modules', []))

        # Init modules before starting the runner so monitor mode does not
        # miss the first burst of workbench traffic.
        self.modules = {}
        for name in self.conf['modules']:
            module = importlib.import_module(f'modules.{name}')
            module_instance = getattr(module, module._modname)(self.can_runner)
            self.modules[name] = module_instance
            self.can_runner.modules[name] = module_instance
            if hasattr(module_instance, 'on_can_message'):
                self.can_runner.listen(None, module_instance.on_can_message)

            if not tabs.tab_list:
                tabs.add_widget(module_instance)
                Clock.schedule_once(partial(tabs.switch_to, module_instance))
            else:
                tabs.add_widget(module_instance)

        self.can_runner.run()
        Clock.schedule_interval(self.can_runner.process_events, 0)

    def on_stop(self):
        logging.info('closing app')
        self.can_runner.stop()
        self.thread_exit = True

if __name__ == '__main__':
    args = parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
    )
    monitor_mode = args.monitor or args.mode == 'monitor'
    PeugeotSim(
        monitor=monitor_mode,
        channel=args.channel,
        interface=args.interface,
        bitrate=args.bitrate,
    ).run()
