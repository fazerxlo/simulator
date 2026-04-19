import datetime
import logging
import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Clim'
_version = '0.0.1'

logger = logging.getLogger(__name__)

class Clim(TabbedPanelItem):
    _ignition_on = 0x01

    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Clim'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/clim.kv')
        Builder.apply(self)

        # Register CAN callbacks
        logger.debug('registering climate module')
        # Note: Msg1D0, Msg1E3, and Msg12D are registered by bsi-base and switch
        # to full climate encoding when car.clim.enabled is True.  No separate TX
        # registration is needed here.
        runner.car.clim.enabled = True

        # Initialise climate state on the shared VirtualCar.
        clim = runner.car.clim
        clim.fan = 2
        clim.dir_left = 0
        clim.dir_right = 0
        clim.temp_left = 11
        clim.temp_right = 11
        clim.unfrost_front = 0
        clim.unfrost_rear = 0
        clim.recycle = 0
        clim.auto = 1   # default: AUTO airflow mode on startup
        clim.ac = 1     # default: A/C compressor on
        clim.dual = 0
        clim.bits = 0

        self.temp_disp = [
            'MIN',
            '14',
            '15',
            '16',
            '17',
            '18', '18.5',
            '19', '19.5',
            '20', '20.5',
            '21', '21.5',
            '22', '22.5',
            '23', '23.5',
            '24',
            '25',
            '26',
            '27',
            '28',
            'HI'
        ]

        self._update_fan(clim.fan)
        self._update_temps()
        self._update_options()
        self._update_dir_buttons()

    @property
    def _clim(self):
        """Convenience accessor for the shared climate car state."""
        return self.runner.car.clim

    def _is_ignition_on(self):
        return bool(self.runner.car.bsi.ignition_on)

    def _set_off_state(self):
        clim = self._clim
        clim.fan = 0
        clim.dir_left = 0
        clim.dir_right = 0
        clim.bits = 0
        clim.unfrost_front = 0
        clim.unfrost_rear = 0
        clim.recycle = 0
        clim.auto = 0
        clim.intake_explicit = False
        self._update_fan(clim.fan)
        self._update_temps()
        self._update_options()
        self._update_dir_buttons()

    def on_dir(self, seat, dir, state='down'):
        if state != 'down' or not self._is_ignition_on():
            return
        clim = self._clim
        # Pressing a non-auto direction button while AUTO mode is active
        # automatically exits AUTO mode (switches to FRESH: no recycle, no defrost).
        if clim.auto and dir != 0x00:
            clim.auto = 0
            self._update_options()
        if seat == 0:
            clim.dir_left = dir
            if not clim.dual:
                # In mono mode the right zone is not independently adjustable,
                # so mirror the selected airflow direction immediately.
                clim.dir_right = dir
        else:
            if not clim.dual and clim.dir_left != dir:
                clim.dual = 1
                self._update_options()
            clim.dir_right = dir
        self._update_dir_buttons()

    def on_clim_on(self, state):
        clim = self._clim
        clim.enabled = (state == 'down')
        logger.info('Climate panel %s', 'ON' if state == 'down' else 'OFF')
        if not clim.enabled:
            # Reset climate state so the BSI idle frames are sent.
            self._set_off_state()
            clim.enabled = False  # _set_off_state does not touch enabled
        self._update_options()

    def on_ac(self, state):
        if not self._is_ignition_on():
            self._update_options()
            return
        self._clim.ac = 1 if state == 'down' else 0
        if self._clim.ac == 0 and self._clim.auto:
            # Generic AUTO relies on A/C being active on this bench. Turning A/C
            # off exits AUTO mode and falls back to manual airflow management.
            self._clim.auto = 0
        logger.info('A/C %s', 'ON' if state == 'down' else 'OFF')
        self._update_options()

    def on_airflow_mode(self, mode, state='down'):
        """Handle the mutually exclusive airflow-mode button group.

        Modes:
        - 'auto'          : A/C AUTO — resets both direction zones to 0x00
        - 'unfrost_front' : Front windscreen demist
        - 'recirc'        : Cabin recirculation
        - 'fresh'         : Outside fresh air (no auto, no defrost, no recirculation)
        """
        if state != 'down' or not self._is_ignition_on():
            self._update_options()
            return
        clim = self._clim
        # Capture prior state BEFORE modifying clim.auto / clim.enabled below —
        # these flags govern popup and re-enable logic and must reflect the
        # state the user was in when the button was pressed.
        was_active_non_auto = clim.enabled and not clim.auto
        was_standby = not clim.enabled
        clim.auto = 1 if mode == 'auto' else 0
        clim.unfrost_front = 1 if mode == 'unfrost_front' else 0
        clim.recycle = 1 if mode == 'recirc' else 0
        # AUTO clears the explicit-intake flag; any other mode sets it to
        # mark that the user has deliberately selected a non-AUTO intake mode.
        # This gates the bit2 (0x04) mode indicator in 0x1E3 byte0 and the
        # bit5 (0x20) non-auto flag in 0x1D0 byte4 (workbench-verified).
        clim.intake_explicit = (mode != 'auto')
        # Workbench-verified: recirc and fresh modes turn the A/C compressor off;
        # AUTO mode turns it back on.  unfrost_front leaves A/C unchanged.
        if mode in ('recirc', 'fresh'):
            clim.ac = 0
            # Set the one-shot notification flag so that the next 0x1E3 frame
            # includes bit1 (0x02) — the real BSI does this for exactly one
            # frame to trigger the MFD popup ("Cabin air recycling activated"
            # for recirc, "Forced intake of outside air" for fresh).
            # Workbench: 0x87 = 0x85|0x02 on recirc entry; 0x07 = 0x05|0x02
            # on fresh entry.  See workbench_airflow.csv analysis.
            clim.intake_notify = True
        if mode == 'auto':
            # In AUTO mode the climate controller manages direction; reset to auto.
            clim.dir_left = 0x00
            clim.dir_right = 0x00
            clim.ac = 1  # AUTO mode always has A/C on
            self._update_dir_buttons()
            if was_standby:
                # Pressing AUTO while in standby (fan=0) re-enables climate at
                # minimum fan speed — workbench-verified: fan=1 after AUTO from standby.
                clim.enabled = True
                self._update_fan(1)
            elif was_active_non_auto:
                # Transition from an active non-AUTO mode (recirc/fresh/unfrost) to AUTO:
                # show MFD popup — workbench: flag=0x80, msg_id=0x08, display=0x41.
                mfd = self.runner.car.mfd_popup
                mfd.msg_id = 0x08
                mfd.flag = 0x80
                mfd.display_flags = 0x41
        logger.info('Climate airflow mode: %s', mode)
        self._update_options()

    def on_temp(self, zone, dir):
        if not self._is_ignition_on():
            return
        clim = self._clim
        if zone == 1 and not clim.dual:
            clim.dual = 1
            self._update_options()
        temp = clim.temp_left if zone == 0 else clim.temp_right
        max_temp_idx = len(self.temp_disp) - 1
        if not (temp == 0 and dir == -1) and not (temp == max_temp_idx and dir == +1):
            temp += dir
            if zone == 0:
                clim.temp_left = temp
                if not clim.dual:
                    # Mono mode: keep both zones in sync.
                    clim.temp_right = temp
                    if 'cur_temp1' in self.ids:
                        self.ids['cur_temp1'].text = f'{self._temp_label(temp)}c'
            else:
                clim.temp_right = temp
            zone_name = 'left' if zone == 0 else 'right'
            logger.info('Climate %s temperature set to %s°C', zone_name, self._temp_label(temp))
            self.ids[f'cur_temp{zone}'].text = f'{self._temp_label(temp)}c'

    def on_option(self, option, value):
        if not self._is_ignition_on():
            self._update_options()
            return
        clim = self._clim
        new_value = 1 if value == 'down' else 0
        setattr(clim, option, new_value)
        if option == 'dual' and not new_value:
            # In mono mode the right zone is no longer independently adjustable,
            # so mirror the left-side settings immediately.
            clim.temp_right = clim.temp_left
            clim.dir_right = clim.dir_left
            self._update_temps()
            self._update_dir_buttons()
        state_str = 'on' if value == 'down' else 'off'
        logger.info('Climate %s %s', option.replace('_', ' '), state_str)
        self._update_options()

    def on_intake(self, recirculate, state='down'):
        if state != 'down' or not self._is_ignition_on():
            self._update_options()
            return
        self._clim.recycle = 1 if recirculate else 0
        self._clim.intake_explicit = True  # explicit intake mode selection
        logger.info('Climate intake %s', 'recirculate' if recirculate else 'fresh/outside')
        self._update_options()

    def on_fan(self, value):
        if not self._is_ignition_on():
            self._update_fan(self._clim.fan)
            return
        new_fan = self._normalize_ui_fan(value)
        if self._clim.fan == 0 and new_fan > 0:
            # Raising fan from 0 always exits standby mode; re-enable climate if needed.
            self._clim.enabled = True
            self._update_options()
            logger.info('Climate enabled from standby by raising fan from 0')
        if new_fan != self._clim.fan:
            logger.info('Fan speed set to %d', new_fan)
        if new_fan == 0:
            # Fan=0 suspends climate but preserves all settings (ac, dual,
            # direction, temps) so they can be restored when fan is raised again.
            self._clim.enabled = False
            self._update_fan(0)
            # Workbench: at fan=0 (standby) 0x1A1 transitions to flag=0x00,
            # msg_id=0x65, display=0x41.
            mfd = self.runner.car.mfd_popup
            mfd.flag = 0x00
            mfd.msg_id = 0x65
            mfd.display_flags = 0x41
            self._update_options()
            return
        clim = self._clim
        if not clim.enabled:
            # Re-enable from standby when user raises fan from 0.
            clim.enabled = True
        if clim.auto:
            # Changing fan speed manually always exits AUTO mode.
            clim.auto = 0
            self._update_options()
        self._update_fan(new_fan)

    def on_toggle(self, bit, value):
        if not self._is_ignition_on():
            return
        if value == 'down':
            self._clim.bits |= 1 << bit
        else:
            self._clim.bits &= ~(1 << bit)

    def _normalize_ui_fan(self, raw_value):
        if raw_value is None:
            return self._clim.fan
        fan = int(raw_value)
        return fan if 0 <= fan <= 8 else self._clim.fan

    def _decode_can_fan(self, raw_value):
        if raw_value is None:
            return self._clim.fan
        raw = int(raw_value) & 0x0F
        if raw == 0x0F:
            return 0
        if 0 <= raw <= 7:
            return raw + 1
        return self._clim.fan

    def _normalize_dir(self, raw_value):
        if raw_value is None:
            return 0
        value = int(raw_value) & 0xFF
        return (value >> 4) if value > 0x0F else (value & 0x0F)

    def _temp_label(self, raw_temp):
        if 0 <= raw_temp < len(self.temp_disp):
            return self.temp_disp[raw_temp]
        return str(raw_temp)

    def _update_fan(self, fan):
        self._clim.fan = fan
        if 'slider_fan' in self.ids and self.ids['slider_fan'].value != fan:
            self.ids['slider_fan'].value = fan
        if 'cur_fan' in self.ids:
            self.ids['cur_fan'].text = f'Fan: {fan}'

    def _update_dir_buttons(self):
        clim = self._clim
        dir_to_suffix = {
            0x00: 'auto',
            0x02: 'down',
            0x03: 'fr',
            0x04: 'up',
            0x05: 'fd',
            0x06: 'ud',
            0x07: 'all',
            0x08: 'fast',
        }
        for seat, prefix in [(0, 'left'), (1, 'right')]:
            if clim.auto:
                # In AUTO mode both direction grids always show 'auto' selected.
                target_id = f'{prefix}_auto'
            else:
                dir_val = self._normalize_dir(clim.dir_left if seat == 0 else clim.dir_right)
                target_suffix = dir_to_suffix.get(dir_val)
                target_id = f'{prefix}_{target_suffix}' if target_suffix else None
            for state_id in [f'{prefix}_auto', f'{prefix}_fr', f'{prefix}_up', f'{prefix}_ud',
                             f'{prefix}_down', f'{prefix}_fd', f'{prefix}_all', f'{prefix}_fast']:
                if state_id not in self.ids:
                    continue
                desired_state = 'down' if state_id == target_id else 'normal'
                if self.ids[state_id].state != desired_state:
                    self.ids[state_id].state = desired_state

    def _update_temps(self):
        clim = self._clim
        if 'cur_temp0' in self.ids:
            self.ids['cur_temp0'].text = f'{self._temp_label(clim.temp_left)}c'
        if 'cur_temp1' in self.ids:
            self.ids['cur_temp1'].text = f'{self._temp_label(clim.temp_right)}c'

    def _update_options(self):
        clim = self._clim
        # ON / A/C power buttons
        if 'clim_on' in self.ids:
            self.ids['clim_on'].state = 'down' if clim.enabled else 'normal'
        if 'ac_on' in self.ids:
            self.ids['ac_on'].state = 'down' if clim.ac else 'normal'
        if 'dual' in self.ids:
            self.ids['dual'].state = 'down' if clim.dual else 'normal'
        if 'unfrost_rear' in self.ids:
            self.ids['unfrost_rear'].state = 'down' if clim.unfrost_rear else 'normal'
        # Mutually exclusive airflow-mode group
        mode = self._get_airflow_mode()
        for m_id, m_key in [
            ('mode_auto', 'auto'),
            ('mode_unfrost_front', 'unfrost_front'),
            ('mode_recirc', 'recirc'),
            ('mode_fresh', 'fresh'),
        ]:
            if m_id in self.ids:
                self.ids[m_id].state = 'down' if mode == m_key else 'normal'
        # Backward compat: old ids used by monitor mode and legacy tests
        if 'auto' in self.ids:
            self.ids['auto'].state = 'down' if clim.auto else 'normal'
        if 'intake_fresh' in self.ids:
            self.ids['intake_fresh'].state = 'normal' if clim.recycle else 'down'
        if 'intake_recycle' in self.ids:
            self.ids['intake_recycle'].state = 'down' if clim.recycle else 'normal'
        if 'recycle' in self.ids:
            self.ids['recycle'].state = 'down' if clim.recycle else 'normal'
        if 'unfrost_front' in self.ids:
            self.ids['unfrost_front'].state = 'down' if clim.unfrost_front else 'normal'

    def _get_airflow_mode(self):
        """Return the active airflow mode key for the mutex button group."""
        clim = self._clim
        if clim.auto:
            return 'auto'
        if clim.unfrost_front:
            return 'unfrost_front'
        if clim.recycle:
            return 'recirc'
        return 'fresh'

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x036 and len(msg.data) >= 5:
            if int(msg.data[4]) != self._ignition_on:
                self._set_off_state()
        elif msg.arbitration_id == 0x1D0 and len(msg.data) >= 7:
            self._update_fan(self._decode_can_fan(msg.data[2]))
            raw_dir = int(msg.data[3]) & 0xFF
            high = (raw_dir >> 4) & 0x0F
            low = raw_dir & 0x0F
            if high and high == low:
                self._clim.dir_left = high
            self._clim.recycle = (msg.data[4] >> 4) & 1
            # Note: bit5 of byte4 = "non-auto intake" flag; unfrost_front decoded from 0x1E3
            self._clim.temp_left = msg.data[5]
            self._clim.temp_right = msg.data[6]
            self._update_temps()
            self._update_options()
            self._update_dir_buttons()
        elif msg.arbitration_id == 0x1E3 and len(msg.data) >= 7:
            self._update_fan(self._decode_can_fan(msg.data[6]))
            self._clim.dir_left = msg.data[4] >> 4
            self._clim.dir_right = msg.data[5] >> 4
            self._clim.ac = (msg.data[0] >> 4) & 1
            self._clim.auto = (msg.data[0] >> 3) & 1
            self._clim.dual = msg.data[0] & 1
            # bit7 of byte0 = recirculation indicator (workbench-verified).
            self._clim.recycle = (msg.data[0] >> 7) & 1
            self._clim.unfrost_front = (msg.data[1] >> 7) & 1
            self._clim.temp_left = msg.data[2] & 0x1F
            self._clim.temp_right = msg.data[3]
            self._update_temps()
            self._update_options()
            self._update_dir_buttons()

