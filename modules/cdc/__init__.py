import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from can_messages import Msg1A0, Msg131

_modname = 'CDC'
_modversion = '0.0.1'


class CDC(TabbedPanelItem):
    """CD changer simulator panel.

    Emulates a PSA CAN2004 CD changer by transmitting 0x1A0 (status) frames
    and decoding received 0x131 (command) frames from the head unit.

    The UI allows manual control of playback state, disc and track selection,
    elapsed time tracking, and playback mode flags.
    """

    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'CDC'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/cdc.kv')
        Builder.apply(self)

        # Register CAN message objects
        print('registering CDC CAN messages')
        runner.register_message(Msg1A0())
        runner.register_message(Msg131())

        # Activate CDC in the shared car state
        runner.car.cdc.active = True

        # Clock handle for the playback time ticker
        self._timer = None

        # Sync initial UI state
        self._update_ui()

    @property
    def _cdc(self):
        """Convenience accessor for the shared CDC car state."""
        return self.runner.car.cdc

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    def on_play(self):
        """Start or resume playback."""
        self._cdc.status = self._cdc.STATUS_PLAYING
        self._update_ui()
        self._start_timer()

    def on_pause(self):
        """Pause or resume playback (toggle)."""
        cdc = self._cdc
        if cdc.status == cdc.STATUS_PLAYING:
            cdc.status = cdc.STATUS_PAUSED
            self._stop_timer()
        elif cdc.status == cdc.STATUS_PAUSED:
            cdc.status = cdc.STATUS_PLAYING
            self._start_timer()
        self._update_ui()

    def on_stop(self):
        """Stop playback and reset track time."""
        cdc = self._cdc
        cdc.status = cdc.STATUS_IDLE
        cdc.minutes = 0
        cdc.seconds = 0
        self._stop_timer()
        self._update_ui()

    def on_next_track(self):
        """Advance to the next track (wraps around)."""
        cdc = self._cdc
        cdc.track = (cdc.track % cdc.total_tracks) + 1
        cdc.minutes = 0
        cdc.seconds = 0
        self._update_ui()

    def on_prev_track(self):
        """Go back to the previous track (wraps around)."""
        cdc = self._cdc
        cdc.track = cdc.total_tracks if cdc.track <= 1 else cdc.track - 1
        cdc.minutes = 0
        cdc.seconds = 0
        self._update_ui()

    def on_next_disc(self):
        """Advance to the next disc (wraps around 1-6)."""
        cdc = self._cdc
        cdc.disc = (cdc.disc % 6) + 1
        cdc.track = 1
        cdc.minutes = 0
        cdc.seconds = 0
        cdc.status = cdc.STATUS_SEARCHING
        self._stop_timer()
        self._update_ui()

    def on_prev_disc(self):
        """Go back to the previous disc (wraps around 1-6)."""
        cdc = self._cdc
        cdc.disc = 6 if cdc.disc <= 1 else cdc.disc - 1
        cdc.track = 1
        cdc.minutes = 0
        cdc.seconds = 0
        cdc.status = cdc.STATUS_SEARCHING
        self._stop_timer()
        self._update_ui()

    def on_disc(self, disc_num, state):
        """Select a specific disc via the toggle buttons."""
        if state != 'down':
            return
        cdc = self._cdc
        if disc_num != cdc.disc:
            cdc.disc = disc_num
            cdc.track = 1
            cdc.minutes = 0
            cdc.seconds = 0
            cdc.status = cdc.STATUS_SEARCHING
            self._stop_timer()
            self._update_ui()

    def on_total_tracks(self, value):
        """Update the total-tracks count from the slider."""
        try:
            v = int(value)
            if 1 <= v <= 99:
                self._cdc.total_tracks = v
                if 'total_tracks_label' in self.ids:
                    self.ids['total_tracks_label'].text = str(v)
        except (ValueError, TypeError):
            pass

    def on_mode(self, mode, state):
        """Update a playback mode flag from its toggle button."""
        cdc = self._cdc
        val = (state == 'down')
        if mode == 'random':
            cdc.random = val
        elif mode == 'repeat':
            cdc.repeat = val
        elif mode == 'repeat_track':
            cdc.repeat_track = val
        elif mode == 'scan':
            cdc.scan = val

    # ------------------------------------------------------------------
    # Timer for elapsed time tracking
    # ------------------------------------------------------------------

    def _start_timer(self):
        if self._timer:
            self._timer.cancel()
        self._timer = Clock.schedule_interval(self._tick, 1.0)

    def _stop_timer(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _tick(self, dt):
        cdc = self._cdc
        if cdc.status != cdc.STATUS_PLAYING:
            return
        cdc.seconds += 1
        if cdc.seconds >= 60:
            cdc.seconds = 0
            cdc.minutes += 1
        self._update_ui()

    # ------------------------------------------------------------------
    # UI synchronisation
    # ------------------------------------------------------------------

    def _update_ui(self):
        cdc = self._cdc
        status_texts = {
            cdc.STATUS_IDLE: 'Stopped',
            cdc.STATUS_PLAYING: 'Playing',
            cdc.STATUS_PAUSED: 'Paused',
            cdc.STATUS_LOADING: 'Loading',
            cdc.STATUS_SEARCHING: 'Searching',
        }
        if 'status_label' in self.ids:
            self.ids['status_label'].text = status_texts.get(cdc.status, 'Unknown')
        if 'disc_label' in self.ids:
            self.ids['disc_label'].text = f'Disc: {cdc.disc}'
        if 'track_label' in self.ids:
            self.ids['track_label'].text = f'Track: {cdc.track}/{cdc.total_tracks}'
        if 'time_label' in self.ids:
            self.ids['time_label'].text = f'{cdc.minutes:02d}:{cdc.seconds:02d}'
        # Sync disc toggle buttons (guard against feedback loops)
        for i in range(1, 7):
            btn_id = f'disc_{i}'
            if btn_id in self.ids:
                desired = 'down' if i == cdc.disc else 'normal'
                if self.ids[btn_id].state != desired:
                    self.ids[btn_id].state = desired
        # Sync total tracks slider
        if 'total_tracks_slider' in self.ids:
            if self.ids['total_tracks_slider'].value != cdc.total_tracks:
                self.ids['total_tracks_slider'].value = cdc.total_tracks
        if 'total_tracks_label' in self.ids:
            self.ids['total_tracks_label'].text = str(cdc.total_tracks)

    # ------------------------------------------------------------------
    # CAN receive callback
    # ------------------------------------------------------------------

    def on_can_message(self, msg):
        """Handle received CAN frames relevant to the CDC module.

        The runner's Msg131.decode() has already updated car.cdc by the
        time this callback fires; we just need to sync the UI.
        """
        if msg.arbitration_id == 0x131:
            # Msg131.decode() already ran in the receiver thread;
            # update UI to reflect any state changes.
            cdc = self._cdc
            if cdc.status == cdc.STATUS_PLAYING and self._timer is None:
                self._start_timer()
            elif cdc.status != cdc.STATUS_PLAYING and self._timer is not None:
                self._stop_timer()
            self._update_ui()
